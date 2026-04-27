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

def publish_attack_rejection(proposal, kind, reason):
    logger.warning(f"🚨 ATTACK DETECTED: {kind} - {reason}")

def run_patriarch_daemon():
    """Runs Process 2 (The Patriarch) as a continuous listener on the AXL network."""
    logger.info("Initializing Patriarch Process (Node B)...")
    axl_node = MockAXLNode(node_id="Patriarch_Node_B", url_env="AXL_NODE_URL_PATRIARCH")
    firewall = PolicyFirewall()
    memory_manager = MemoryManager()
    treasury = SafeTreasury()
    router = UniswapV4Router()
    last_proposal_id = 0
    
    negotiation_transcripts = {}
    logger.info("Patriarch listening for new Proposals...")
    
    while True:
        try:
            proposal_messages = axl_node.subscribe(topic="PROPOSALS", last_id=last_proposal_id)
            for msg in proposal_messages:
                last_proposal_id = msg["id"]
                proposal_dict = msg["payload"]
                proposal = Proposal(**proposal_dict)
                root_id = proposal.proposal_id.split("_v")[0]
                
                logger.info(f"Received Proposal {proposal.proposal_id} from {msg['sender']}. Evaluating...")

                if not proposal.quant_signature:
                    publish_attack_rejection(proposal, "INVALID_SIGNATURE", "Missing Quant signature")
                    continue
                
                sig_bundle_q = "0x" + proposal.quant_signature[2:132]
                sig_safe_q   = "0x" + proposal.quant_signature[132:]
                
                p_digest = proposal_eip712_digest(proposal.model_dump(by_alias=True), treasury.safe_address or "0x0", proposal.chain_id)
                b_digest = bundle_hash(p_digest, bytes.fromhex(proposal.safe_tx_hash[2:]))
                
                if recover_signer(b_digest, sig_bundle_q) != QUANT_ADDR:
                    publish_attack_rejection(proposal, "INVALID_SIGNATURE", "Quant bundle sig mismatch")
                    continue
                
                state = {"incoming_proposal": proposal, "messages": [], "market_data": {}} # Simplified md
                result = patriarch_app.invoke(state)
                reviewed_proposal: Proposal = result.get("reviewed_proposal")
                
                if reviewed_proposal:
                    if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                        calldata = router.generate_calldata(reviewed_proposal)
                        attestation = simulate_with_keeperhub(reviewed_proposal, calldata)
                        
                        if attestation and attestation.status == "REVERT":
                            publish_attack_rejection(reviewed_proposal, "SIM_FAILURE", "Simulation reverted.")
                            reviewed_proposal.consensus_status = ConsensusStatus.REJECTED
                            reviewed_proposal.rationale += " | OVERRIDE: Simulation failed."
                        else:
                            try:
                                if firewall.validate_proposal(reviewed_proposal):
                                    axl_node.publish(topic="FIREWALL_CLEARED", payload=reviewed_proposal.model_dump())
                                    if reviewed_proposal.safe_tx_hash and PATRIARCH_KEY:
                                        sig_bundle_p = sign_digest(b_digest, PATRIARCH_KEY)
                                        sig_safe_p   = sign_digest(bytes.fromhex(reviewed_proposal.safe_tx_hash[2:]), PATRIARCH_KEY)
                                        reviewed_proposal.patriarch_signature = sig_bundle_p + sig_safe_p[2:]
                                        
                                        consensus_msg = ConsensusMessage(
                                            proposal_id=reviewed_proposal.proposal_id,
                                            signer_id="Patriarch_Node_B",
                                            signer_address=PATRIARCH_ADDR,
                                            signature=sig_safe_p,
                                            safe_tx_hash=reviewed_proposal.safe_tx_hash,
                                            timestamp=time.time()
                                        )
                                        axl_node.publish(topic="CONSENSUS_SIGNATURES", payload=consensus_msg.model_dump())
                                    
                                    full_transcript = json.dumps(negotiation_transcripts.get(root_id, []), indent=2)
                                    memory_manager.save_decision(reviewed_proposal.model_dump(), full_transcript)
                            except ValueError as e:
                                logger.error(f"❌ FIREWALL REJECTED: {e}")

                    if root_id not in negotiation_transcripts:
                        negotiation_transcripts[root_id] = []
                    negotiation_transcripts[root_id].append({
                        "iteration": proposal.proposal_id,
                        "status": reviewed_proposal.consensus_status.value,
                        "rationale": reviewed_proposal.rationale
                    })
                    axl_node.publish(topic="PROPOSAL_EVALUATIONS", payload=reviewed_proposal.model_dump())
            time.sleep(2)
        except KeyboardInterrupt: break
        except Exception as e:
            logger.error(f"Error in Patriarch daemon: {e}")
            time.sleep(5)

if __name__ == "__main__":
    load_dotenv()
    run_patriarch_daemon()
