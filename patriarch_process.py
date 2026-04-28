import time
import logging
import json
import os
from dotenv import load_dotenv
from core.network import MockAXLNode
from core.models import Proposal, ConsensusStatus, ConsensusMessage
from agents.patriarch import patriarch_app
from execution.firewall import PolicyFirewall
from memory.memory_manager import MemoryManager
from execution.safe_treasury import SafeTreasury
from core.crypto import proposal_eip712_digest, bundle_hash, sign_digest, recover_signer
from core.identity import QUANT_ADDR, PATRIARCH_ADDR, PATRIARCH_KEY
from execution.keeper_hub import simulate_with_keeperhub
from execution.uniswap_v4.router import UniswapV4Router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchProcess")


def publish_attack_rejection(axl_node: MockAXLNode, proposal: Proposal, kind: str, reason: str):
    logger.warning(f"🚨 ATTACK DETECTED [{kind}]: {reason}")
    rejection = {
        "attack_id": f"atk_{int(time.time())}",
        "attacker_node_id": "unknown",
        "attack_kind": kind,
        "detected_at": time.time(),
        "detected_by": "Patriarch_Node_B",
        "evidence": {"proposal_id": proposal.proposal_id},
        "rejection_reason": reason,
        "publish_to_0g": True,
    }
    axl_node.publish(topic="ATTACK_REJECTED", payload=rejection)
    # Write forensic record to 0G
    try:
        mm = MemoryManager()
        mm.write_artifact("AttackRejection", rejection)
    except Exception as e:
        logger.error(f"Failed to write AttackRejection to 0G: {e}")


def run_patriarch_daemon():
    logger.info("Initializing Patriarch Process (Node B)...")
    axl_node = MockAXLNode(node_id="Patriarch_Node_B", url_env="AXL_NODE_URL_PATRIARCH")
    firewall = PolicyFirewall()
    memory_manager = MemoryManager()
    treasury = SafeTreasury()
    router = UniswapV4Router()

    last_proposal_id = 0
    last_snapshot_id = 0
    negotiation_transcripts = {}

    # Cache of market_snapshot_hash -> market_data, populated from MARKET_SNAPSHOTS topic
    snapshot_cache: dict[str, dict] = {}

    logger.info("Patriarch listening for Proposals and Market Snapshots...")

    while True:
        try:
            # 1. Cache incoming market snapshots so we can feed them to the recheck
            snapshot_messages = axl_node.subscribe(topic="MARKET_SNAPSHOTS", last_id=last_snapshot_id)
            for msg in snapshot_messages:
                last_snapshot_id = msg["id"]
                snap = msg["payload"]
                h = snap.get("market_snapshot_hash")
                if h:
                    snapshot_cache[h] = snap.get("market_data", {})
                    logger.debug(f"Cached market snapshot {h[:12]}...")

            # 2. Process proposals
            proposal_messages = axl_node.subscribe(topic="PROPOSALS", last_id=last_proposal_id)
            for msg in proposal_messages:
                last_proposal_id = msg["id"]
                proposal_dict = msg["payload"]
                proposal = Proposal(**proposal_dict)
                root_id = proposal.proposal_id.split("_v")[0]

                logger.info(f"Received Proposal {proposal.proposal_id} from {msg['sender']}.")

                # --- Signature verification ---
                if not proposal.quant_signature:
                    publish_attack_rejection(axl_node, proposal, "INVALID_SIGNATURE", "Missing quant_signature")
                    continue

                if not proposal.safe_tx_hash:
                    publish_attack_rejection(axl_node, proposal, "INVALID_SIGNATURE", "Missing safe_tx_hash")
                    continue

                sig_bundle_q = "0x" + proposal.quant_signature[2:132]
                sig_safe_q   = "0x" + proposal.quant_signature[132:]

                p_digest = proposal_eip712_digest(
                    proposal.model_dump(by_alias=True),
                    treasury.safe_address or "0x0000000000000000000000000000000000000000",
                    proposal.chain_id,
                )
                b_digest = bundle_hash(p_digest, bytes.fromhex(proposal.safe_tx_hash[2:]))

                if recover_signer(b_digest, sig_bundle_q) != QUANT_ADDR:
                    publish_attack_rejection(axl_node, proposal, "INVALID_SIGNATURE", "Quant bundle sig mismatch")
                    continue

                # --- Look up market data for deterministic recheck ---
                market_data = snapshot_cache.get(proposal.market_snapshot_hash or "", {})
                if not market_data:
                    logger.warning(f"No cached market snapshot for {proposal.market_snapshot_hash}. Recheck will fail.")

                # --- Run LangGraph (deterministic recheck → LLM eval) ---
                state = {
                    "incoming_proposal": proposal,
                    "messages": [],
                    "market_data": market_data,
                }
                result = patriarch_app.invoke(state)
                reviewed_proposal: Proposal = result.get("reviewed_proposal")

                if reviewed_proposal is None:
                    logger.error(f"patriarch_app returned no reviewed_proposal for {proposal.proposal_id}")
                    continue

                if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                    # --- KeeperHub simulation oracle ---
                    calldata = router.generate_calldata(reviewed_proposal)
                    attestation = simulate_with_keeperhub(reviewed_proposal, calldata)

                    if attestation and attestation.status == "REVERT":
                        publish_attack_rejection(axl_node, reviewed_proposal, "SIM_REVERT", "KeeperHub simulation reverted")
                        reviewed_proposal.consensus_status = ConsensusStatus.REJECTED
                        reviewed_proposal.rationale += " | OVERRIDE: Simulation reverted."
                    else:
                        try:
                            if firewall.validate_proposal(reviewed_proposal):
                                axl_node.publish(topic="FIREWALL_CLEARED", payload=reviewed_proposal.model_dump())

                                # Sign and publish Patriarch's consensus signature
                                if reviewed_proposal.safe_tx_hash and PATRIARCH_KEY:
                                    sig_bundle_p = sign_digest(b_digest, PATRIARCH_KEY)
                                    sig_safe_p   = sign_digest(bytes.fromhex(reviewed_proposal.safe_tx_hash[2:]), PATRIARCH_KEY)
                                    reviewed_proposal.patriarch_signature = sig_bundle_p + sig_safe_p[2:]

                                    consensus_msg = ConsensusMessage(
                                        proposal_id=reviewed_proposal.proposal_id,
                                        iteration=reviewed_proposal.iteration,
                                        signer_id="Patriarch_Node_B",
                                        signer_address=PATRIARCH_ADDR,
                                        signature=sig_safe_p,
                                        safe_tx_hash=reviewed_proposal.safe_tx_hash,
                                        timestamp=time.time(),
                                    )
                                    axl_node.publish(topic="CONSENSUS_SIGNATURES", payload=consensus_msg.model_dump())
                                    logger.info(f"Published Patriarch CONSENSUS_SIGNATURE for {reviewed_proposal.proposal_id}")

                                full_transcript = json.dumps(negotiation_transcripts.get(root_id, []), indent=2)
                                memory_manager.save_decision(reviewed_proposal.model_dump(), full_transcript)

                        except ValueError as e:
                            logger.error(f"❌ FIREWALL REJECTED: {e}")

                # Track negotiation state
                if root_id not in negotiation_transcripts:
                    negotiation_transcripts[root_id] = []
                negotiation_transcripts[root_id].append({
                    "iteration": proposal.proposal_id,
                    "status": reviewed_proposal.consensus_status.value,
                    "rationale": reviewed_proposal.rationale,
                })
                axl_node.publish(topic="PROPOSAL_EVALUATIONS", payload=reviewed_proposal.model_dump())

            time.sleep(2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in Patriarch daemon: {e}")
            time.sleep(5)


if __name__ == "__main__":
    load_dotenv()
    run_patriarch_daemon()
