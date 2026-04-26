import time
import logging
import json
from core.network import MockAXLNode
from core.models import Proposal, ConsensusStatus
from agents.patriarch import patriarch_app
from execution.firewall import PolicyFirewall
from memory.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchProcess")

def run_patriarch_daemon():
    """Runs Process 2 (The Patriarch) as a continuous listener on the AXL network."""
    logger.info("Initializing Patriarch Process (Node B)...")
    axl_node = MockAXLNode(node_id="Patriarch_Node_B")
    firewall = PolicyFirewall()
    memory_manager = MemoryManager()
    last_proposal_id = 0
    
    # Track negotiation history for audit trail
    # root_proposal_id -> [list of evaluations/rejections]
    negotiation_transcripts = {}
    
    logger.info("Patriarch listening for new Proposals...")
    
    while True:
        try:
            # 1. Listen for new proposals from the Quant
            proposal_messages = axl_node.subscribe(topic="PROPOSALS", last_id=last_proposal_id)
            for msg in proposal_messages:
                last_proposal_id = msg["id"]
                proposal_dict = msg["payload"]
                proposal = Proposal(**proposal_dict)
                
                # Determine root ID for tracking iterations (e.g., prop_123_v2 -> prop_123)
                root_id = proposal.proposal_id.split("_v")[0]
                
                logger.info(f"Received Proposal {proposal.proposal_id} from {msg['sender']}. Evaluating...")
                
                state = {"incoming_proposal": proposal, "messages": []}
                result = patriarch_app.invoke(state)
                reviewed_proposal: Proposal = result.get("reviewed_proposal")
                
                if reviewed_proposal:
                    logger.info(f"Publishing Evaluation for {reviewed_proposal.proposal_id} (Status: {reviewed_proposal.consensus_status.value})")
                    axl_node.publish(topic="PROPOSAL_EVALUATIONS", payload=reviewed_proposal.model_dump())
                    
                    # Store in transcript
                    if root_id not in negotiation_transcripts:
                        negotiation_transcripts[root_id] = []
                    negotiation_transcripts[root_id].append({
                        "iteration": proposal.proposal_id,
                        "status": reviewed_proposal.consensus_status.value,
                        "rationale": reviewed_proposal.rationale
                    })
                    
                    # 2. If Accepted, Route to Process 3 (Firewall)
                    if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
                        logger.info("Consensus REACHED. Routing to Execution Node (Process 3)...")
                        try:
                            if firewall.validate_proposal(reviewed_proposal):
                                logger.info("🔥 FIREWALL PASSED. Proposal is ready for execution.")
                                axl_node.publish(topic="FIREWALL_CLEARED", payload=reviewed_proposal.model_dump())
                                
                                # Construct full transcript for audit trail
                                full_transcript = json.dumps(negotiation_transcripts.get(root_id, []), indent=2)
                                
                                # Save the immutable receipt to 0G & index in ChromaDB
                                memory_manager.save_decision(
                                    proposal=reviewed_proposal.model_dump(),
                                    transcript=full_transcript
                                )
                                
                        except ValueError as e:
                            logger.error(f"❌ FIREWALL REJECTED: {e}")
                            
            time.sleep(2) # Polling interval
            
        except KeyboardInterrupt:
            logger.info("Patriarch Process shutting down.")
            break
        except Exception as e:
            logger.error(f"Error in Patriarch daemon: {e}")
            time.sleep(5)

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
         logger.error("CRITICAL: OPENAI_API_KEY environment variable is not set.")
         exit(1)
         
    run_patriarch_daemon()