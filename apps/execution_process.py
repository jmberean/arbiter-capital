from __future__ import annotations

import logging
import os
import time
import threading

from dotenv import load_dotenv
load_dotenv(override=True)  # must run before core.identity is imported so keys are available at eval time
from eth_utils import keccak

from core.crypto import recover_signer
from core.dedupe import DedupeLedger
from core.identity import SAFE_OWNERS
from core.models import (
    Proposal, ConsensusMessage, ExecutionReceipt, ExecutionFailure, Heartbeat,
)
from core.network import MockAXLNode
from execution.keeper_hub import execute_with_keeperhub
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router
from memory.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ExecutionProcess")


def _heartbeat_loop(axl_node: MockAXLNode, last_proposal_ref: list[str], stop_evt: threading.Event):
    """Publishes a Heartbeat every 10s on the HEARTBEAT topic."""
    while not stop_evt.is_set():
        hb = Heartbeat(
            node_id="Execution_Node_P3",
            role="Execution_Node_P3",
            timestamp=time.time(),
            last_seen_proposal=last_proposal_ref[0] if last_proposal_ref else None,
            git_sha=os.getenv("GIT_SHA"),
        )
        try:
            axl_node.publish(topic="HEARTBEAT", payload=hb.model_dump())
        except Exception as e:
            logger.warning(f"Heartbeat publish failed: {e}")
        stop_evt.wait(10.0)


def _mint_sbt(safe_address: str, receipt_hash: str, zero_g_uri: str) -> tuple[str | None, str | None]:
    """Mint an ArbiterReceipt SBT pointing to the 0G receipt URI.

    Returns (sbt_token_id, sbt_tx_hash). Returns (None, None) if config is
    missing — minting is best-effort and never blocks consensus.
    """
    sbt_addr = os.getenv("ARBITER_RECEIPT_NFT", "")
    rpc = os.getenv("ETH_RPC_URL", "")
    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY", "")
    if not (sbt_addr and rpc and executor_key) or executor_key.startswith("0xabc"):
        logger.info("SBT minting skipped (config missing).")
        return None, None

    try:
        from web3 import Web3
        from eth_account import Account

        w3 = Web3(Web3.HTTPProvider(rpc))
        if not w3.is_connected():
            logger.warning("SBT mint: ETH RPC not connected.")
            return None, None

        executor = Account.from_key(executor_key)

        # Minimal ABI: mintReceipt(bytes32,string) -> uint256
        abi = [{
            "inputs": [
                {"name": "receiptHash", "type": "bytes32"},
                {"name": "zeroGUri", "type": "string"},
            ],
            "name": "mintReceipt",
            "outputs": [{"name": "tokenId", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        }]

        contract = w3.eth.contract(address=Web3.to_checksum_address(sbt_addr), abi=abi)
        receipt_bytes32 = bytes.fromhex(receipt_hash[2:] if receipt_hash.startswith("0x") else receipt_hash).rjust(32, b"\x00")[:32]

        tx = contract.functions.mintReceipt(receipt_bytes32, zero_g_uri).build_transaction({
            "from": executor.address,
            "nonce": w3.eth.get_transaction_count(executor.address),
            "gas": 250000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        })
        signed = w3.eth.account.sign_transaction(tx, executor_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()

        token_id = "0x" + receipt_bytes32.hex()
        logger.info(f"✅ SBT minted: token_id={token_id[:18]}… tx={tx_hash}")
        return token_id, tx_hash

    except Exception as e:
        logger.warning(f"SBT mint failed (continuing): {e}")
        return None, None


def run_execution_daemon():
    logger.info("Initializing Execution Process (Process 3 - Deterministic)...")

    axl_node = MockAXLNode(node_id="Execution_Node_P3", url_env="AXL_NODE_URL_EXEC")
    treasury = SafeTreasury()
    router = UniswapV4Router(
        w3=treasury.w3 if not treasury.mock_mode else None,
        owner=treasury.safe_address if not treasury.mock_mode else None,
    )
    dedupe = DedupeLedger()
    memory_manager = MemoryManager()

    last_cleared_id = 0
    last_sig_id = 0
    THRESHOLD = int(os.getenv("CONSENSUS_THRESHOLD", "2"))

    pending_proposals: dict[str, dict] = {}
    last_proposal_ref: list[str] = [""]

    stop_evt = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(axl_node, last_proposal_ref, stop_evt),
        daemon=True,
    )
    hb_thread.start()

    logger.info(f"Execution Node listening (Threshold: {THRESHOLD})...")

    while True:
        try:
            # 1. Drain CONSENSUS_SIGNATURES
            _now = time.time()
            sig_messages = axl_node.subscribe(topic="CONSENSUS_SIGNATURES", last_id=last_sig_id)
            for msg in sig_messages:
                last_sig_id = msg["id"]
                sig_data = ConsensusMessage(**msg["payload"])
                prop_id = sig_data.proposal_id

                # Discard signatures older than 10 minutes — they belong to a previous
                # daemon session and were signed against a different safe_tx_hash.
                age = _now - (sig_data.timestamp or 0)
                if age > 600:
                    logger.warning(
                        f"Discarding stale signature for {prop_id} (age={age:.0f}s)"
                    )
                    continue

                slot = pending_proposals.setdefault(prop_id, {"proposal": None, "signatures": []})
                if sig_data.signature not in slot["signatures"]:
                    slot["signatures"].append(sig_data.signature)
                    logger.info(
                        f"Collected signature for {prop_id}. Total: {len(slot['signatures'])}"
                    )

            # 2. Drain FIREWALL_CLEARED
            cleared_proposals = axl_node.subscribe(topic="FIREWALL_CLEARED", last_id=last_cleared_id)
            for msg in cleared_proposals:
                last_cleared_id = msg["id"]
                proposal = Proposal(**msg["payload"])
                slot = pending_proposals.setdefault(proposal.proposal_id, {"proposal": None, "signatures": []})
                slot["proposal"] = proposal
                last_proposal_ref[0] = proposal.proposal_id
                logger.info(f"Confirmed Firewall clearance for {proposal.proposal_id}.")

            # 3. Settlement
            for prop_id, data in list(pending_proposals.items()):
                proposal: Proposal = data["proposal"]
                sigs = data["signatures"]

                if not (proposal and proposal.safe_tx_hash):
                    continue

                safe_h = bytes.fromhex(proposal.safe_tx_hash[2:])
                seen: set[str] = set()
                valid_sigs: list[str] = []
                for s in sigs:
                    try:
                        addr = recover_signer(safe_h, s)
                    except Exception:
                        continue
                    if addr in SAFE_OWNERS and addr not in seen:
                        seen.add(addr)
                        valid_sigs.append(s)

                if len(seen) < THRESHOLD:
                    continue

                logger.info(
                    f"🚀 MULTISIG THRESHOLD MET for {prop_id} by {seen}. Proceeding to execution."
                )

                # Dedupe
                if dedupe.already_executed(treasury.safe_address or "0x0", proposal.safe_nonce or 0):
                    logger.warning(
                        f"Nonce {proposal.safe_nonce} already used (dedupe). Rejecting replay."
                    )
                    failure = ExecutionFailure(
                        proposal_id=prop_id,
                        iteration=proposal.iteration,
                        safe_address=treasury.safe_address or "0x0",
                        safe_nonce=proposal.safe_nonce or 0,
                        failure_kind="OTHER",
                        detail="dedupe-replay",
                    )
                    axl_node.publish(topic="EXECUTION_FAILURE", payload=failure.model_dump())
                    memory_manager.write_artifact("ExecutionFailure", failure.model_dump())
                    del pending_proposals[prop_id]
                    continue

                # 4. Build calldata + sigs blob (Safe expects sigs concatenated, sorted by signer addr)
                calldata = router.generate_calldata(proposal)
                sorted_signers = sorted(seen, key=lambda a: int(a, 16))
                sigs_blob = "0x"
                for addr in sorted_signers:
                    sig = next(s for s in valid_sigs if recover_signer(safe_h, s) == addr)
                    raw = sig[2:] if sig.startswith("0x") else sig
                    sigs_blob += raw

                # 5. Execute
                try:
                    tx_hash = treasury.execute_with_signatures(proposal, calldata, [sigs_blob])
                except Exception as e:
                    logger.error(f"❌ Safe execution raised: {e}")
                    failure = ExecutionFailure(
                        proposal_id=prop_id,
                        iteration=proposal.iteration,
                        safe_address=treasury.safe_address or "0x0",
                        safe_nonce=proposal.safe_nonce or 0,
                        failure_kind="REVERT",
                        detail=str(e),
                    )
                    axl_node.publish(topic="EXECUTION_FAILURE", payload=failure.model_dump())
                    memory_manager.write_artifact("ExecutionFailure", failure.model_dump())
                    del pending_proposals[prop_id]
                    continue

                if not tx_hash:
                    logger.error(f"❌ Empty tx_hash for {prop_id}.")
                    del pending_proposals[prop_id]
                    continue

                logger.info(f"✅ EXECUTION COMPLETE for {prop_id}. Tx Hash: {tx_hash}")
                dedupe.mark(treasury.safe_address or "0x0", proposal.safe_nonce or 0, prop_id, tx_hash)

                # 6. Persist ExecutionReceipt to 0G (hash-chained) FIRST so we have its hash for the SBT
                receipt = ExecutionReceipt(
                    proposal_id=prop_id,
                    iteration=proposal.iteration,
                    safe_address=treasury.safe_address or "0x0",
                    safe_nonce=proposal.safe_nonce or 0,
                    tx_hash=tx_hash,
                )
                receipt_tx = memory_manager.write_artifact("ExecutionReceipt", receipt.model_dump())
                receipt_hash = "0x" + keccak(
                    f"{prop_id}-{proposal.safe_nonce}-{tx_hash}".encode()
                ).hex()
                zero_g_uri = f"0g://{receipt_tx}"

                # 7. Mint SBT (best-effort)
                token_id, sbt_tx = _mint_sbt(
                    treasury.safe_address or "0x0",
                    receipt_hash,
                    zero_g_uri,
                )
                if token_id:
                    receipt.sbt_token_id = token_id
                    receipt.sbt_tx_hash = sbt_tx

                axl_node.publish(topic="EXECUTION_SUCCESS", payload=receipt.model_dump())
                del pending_proposals[prop_id]

            time.sleep(2)

        except KeyboardInterrupt:
            logger.info("Execution Process shutting down.")
            stop_evt.set()
            break
        except Exception as e:
            logger.error(f"Error in Execution daemon: {e}")
            time.sleep(5)


if __name__ == "__main__":
    load_dotenv(override=True)
    run_execution_daemon()
