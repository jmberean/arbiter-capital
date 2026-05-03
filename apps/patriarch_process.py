from __future__ import annotations

import json
import logging
import os
import time
import uuid

from dotenv import load_dotenv
load_dotenv(override=True)  # must run before core.identity is imported so keys are available at eval time

from core.crypto import (
    proposal_eip712_digest, bundle_hash, sign_digest, recover_signer,
)
from core.identity import (
    QUANT_ADDR, PATRIARCH_ADDR, PATRIARCH_KEY, is_attestor,
)
from core.models import (
    Proposal, ConsensusStatus, ConsensusMessage, AttackRejection, SimulationRequest,
)
from core.network import MockAXLNode

from agents.patriarch import patriarch_app
from execution.firewall import PolicyFirewall
from execution.keeper_hub import simulate_with_keeperhub
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router
from memory.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchProcess")


def publish_attack_rejection(axl_node: MockAXLNode, proposal: Proposal, kind: str,
                             reason: str, attacker_node: str = "unknown",
                             evidence: dict | None = None):
    logger.warning(f"🚨 ATTACK DETECTED [{kind}]: {reason}")
    rejection = AttackRejection(
        attack_id=f"atk_{uuid.uuid4().hex[:12]}",
        attacker_node_id=attacker_node,
        attack_kind=kind,
        detected_at=time.time(),
        detected_by="Patriarch_Node_B",
        evidence=evidence or {"proposal_id": proposal.proposal_id},
        rejection_reason=reason,
    )
    axl_node.publish(topic="ATTACK_REJECTED", payload=rejection.model_dump())
    try:
        MemoryManager().write_artifact("AttackRejection", rejection.model_dump())
    except Exception as e:
        logger.error(f"Failed to write AttackRejection to 0G: {e}")


def run_patriarch_daemon():
    logger.info("Initializing Patriarch Process (Node B)...")
    axl_node = MockAXLNode(node_id="Patriarch_Node_B", url_env="AXL_NODE_URL_PATRIARCH")
    firewall = PolicyFirewall()
    memory_manager = MemoryManager()
    treasury = SafeTreasury()
    router = UniswapV4Router(
        w3=treasury.w3 if not treasury.mock_mode else None,
        owner=treasury.safe_address if not treasury.mock_mode else None,
    )

    last_proposal_id = 0
    last_snapshot_id = 0
    negotiation_transcripts: dict[str, list] = {}
    snapshot_cache: dict[str, dict] = {}

    logger.info("Patriarch listening for Proposals and Market Snapshots...")
    axl_node.publish("HEARTBEAT", {"node_id": "Patriarch_Node_B", "role": "patriarch", "timestamp": time.time(), "status": "ready"})

    while True:
        try:
            # 1. Cache market snapshots
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
                try:
                    proposal = Proposal(**proposal_dict)
                except Exception as e:
                    logger.warning(f"Malformed proposal payload from {msg.get('sender')}: {e}")
                    continue
                root_id = proposal.proposal_id.split("_v")[0]
                attacker_node = msg.get("sender", "unknown")

                logger.info(f"Received Proposal {proposal.proposal_id} from {attacker_node}.")

                # ── Signature presence ────────────────────────────────────
                if not proposal.quant_signature:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        "Missing quant_signature", attacker_node,
                    )
                    continue
                if not proposal.safe_tx_hash:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        "Missing safe_tx_hash", attacker_node,
                    )
                    continue
                if len(proposal.quant_signature) != 264 and len(proposal.quant_signature) != 262:
                    # 130-byte (260) sig + 130-byte sig with optional 0x → 264 with both 0x;
                    # 262 if first sig has 0x and second is appended without.
                    # Be lenient: just require it to split into two well-formed sigs.
                    pass

                sig_combined = proposal.quant_signature
                # First sig ("bundle") starts with "0x" — extract first 132 chars including 0x
                sig_bundle_q = sig_combined[:132]
                sig_safe_q = "0x" + sig_combined[132:]

                # ── EIP-712 digest reconstruction ─────────────────────────
                p_digest = proposal_eip712_digest(
                    proposal,
                    treasury.safe_address or "0x0000000000000000000000000000000000000000",
                    proposal.chain_id,
                )
                try:
                    safe_h = bytes.fromhex(proposal.safe_tx_hash[2:])
                except ValueError:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        "Malformed safe_tx_hash", attacker_node,
                    )
                    continue
                b_digest = bundle_hash(p_digest, safe_h)

                # ── Quant bundle sig must recover to QUANT_ADDR ──────────
                try:
                    bundle_signer = recover_signer(b_digest, sig_bundle_q)
                except Exception as e:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        f"Quant bundle sig unrecoverable: {e}", attacker_node,
                    )
                    continue
                if QUANT_ADDR is None or bundle_signer != QUANT_ADDR:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        f"Quant bundle sig mismatch: recovered {bundle_signer}, expected {QUANT_ADDR}",
                        attacker_node,
                    )
                    continue

                # ── Quant safe sig must also recover to QUANT_ADDR ───────
                try:
                    safe_signer = recover_signer(safe_h, sig_safe_q)
                except Exception as e:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        f"Quant safe sig unrecoverable: {e}", attacker_node,
                    )
                    continue
                if safe_signer != QUANT_ADDR:
                    publish_attack_rejection(
                        axl_node, proposal, "INVALID_SIGNATURE",
                        f"Quant safe sig mismatch: recovered {safe_signer}, expected {QUANT_ADDR}",
                        attacker_node,
                    )
                    continue

                # ── Cached market data for deterministic recheck ─────────
                market_data = snapshot_cache.get(proposal.market_snapshot_hash or "", {})
                if not market_data:
                    logger.warning(
                        f"No cached snapshot for {proposal.market_snapshot_hash}. Recheck will fail."
                    )

                # ── Run LangGraph (recheck → evaluate → consult_sim_oracle) ─
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

                # ── Publish SIM_ORACLE_REQUEST forensics for this proposal ─
                try:
                    if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                        sim_request = SimulationRequest(
                            request_id=f"req_{uuid.uuid4().hex[:12]}",
                            proposal_id=proposal.proposal_id,
                            iteration=proposal.iteration,
                            safe_address=treasury.safe_address or "0x0",
                            to=os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x" + "0" * 40),
                            value=0,
                            data_hex="0x" + router.generate_calldata(reviewed_proposal).hex(),
                            operation=0,
                            requested_by="Patriarch_Node_B",
                        )
                        axl_node.publish(topic="SIM_ORACLE_REQUEST", payload=sim_request.model_dump())
                except Exception as e:
                    logger.debug(f"Sim request publish skipped: {e}")

                if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                    # Extra sim attestation check (defense-in-depth) ───────
                    calldata = router.generate_calldata(reviewed_proposal)
                    attestation = simulate_with_keeperhub(reviewed_proposal, calldata)

                    if attestation and attestation.status == "REVERT":
                        publish_attack_rejection(
                            axl_node, reviewed_proposal, "SIM_REVERT",
                            "KeeperHub simulation reverted", attacker_node,
                        )
                        reviewed_proposal.consensus_status = ConsensusStatus.REJECTED
                        reviewed_proposal.rationale += " | OVERRIDE: Simulation reverted."

                    elif attestation and attestation.signature and attestation.signature != "0x" + "00" * 65:
                        # Attestor signature must recover to a known attestor
                        try:
                            from core.crypto import sim_result_digest
                            digest = bytes.fromhex(attestation.sim_result_hash[2:])
                            recovered = recover_signer(digest, attestation.signature)
                            if not is_attestor(recovered):
                                publish_attack_rejection(
                                    axl_node, reviewed_proposal, "FAKE_SIM_RESULT",
                                    f"Sim attestor unrecognized: {recovered}", attacker_node,
                                )
                                reviewed_proposal.consensus_status = ConsensusStatus.REJECTED
                                reviewed_proposal.rationale += f" | OUTSIDE_MANDATE: sim attestor {recovered} unrecognized"
                        except Exception as e:
                            logger.warning(f"Sim attestation verification error: {e}")

                # ── Firewall + sign ──────────────────────────────────────
                if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                    try:
                        if firewall.validate_proposal(reviewed_proposal):
                            axl_node.publish(
                                topic="FIREWALL_CLEARED",
                                payload=reviewed_proposal.model_dump(),
                            )

                            if reviewed_proposal.safe_tx_hash and PATRIARCH_KEY:
                                sig_bundle_p = sign_digest(b_digest, PATRIARCH_KEY)
                                sig_safe_p = sign_digest(safe_h, PATRIARCH_KEY)
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
                                axl_node.publish(
                                    topic="CONSENSUS_SIGNATURES",
                                    payload=consensus_msg.model_dump(),
                                )
                                logger.info(
                                    f"Published Patriarch CONSENSUS_SIGNATURE for {reviewed_proposal.proposal_id}"
                                )

                            full_transcript = json.dumps(
                                negotiation_transcripts.get(root_id, []), indent=2
                            )
                            memory_manager.save_decision(reviewed_proposal.model_dump(), full_transcript)
                    except ValueError as e:
                        logger.error(f"❌ FIREWALL REJECTED: {e}")
                        publish_attack_rejection(
                            axl_node, reviewed_proposal, "WHITELIST_BYPASS",
                            f"Firewall reject: {e}", attacker_node,
                            evidence={"proposal_id": reviewed_proposal.proposal_id, "detail": str(e)},
                        )

                # Track negotiation state
                negotiation_transcripts.setdefault(root_id, []).append({
                    "iteration": proposal.proposal_id,
                    "status": reviewed_proposal.consensus_status.value,
                    "rationale": reviewed_proposal.rationale,
                })
                axl_node.publish(
                    topic="PROPOSAL_EVALUATIONS",
                    payload=reviewed_proposal.model_dump(),
                )

            time.sleep(2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in Patriarch daemon: {e}")
            time.sleep(5)


if __name__ == "__main__":
    load_dotenv(override=True)
    run_patriarch_daemon()
