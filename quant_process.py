import time
import logging
import json
from core.network import MockAXLNode
from core.models import Proposal, ConsensusStatus
from agents.quant import quant_app
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantProcess")

def run_quant_daemon():
    """Runs Process 1 (The Quant) as a continuous listener on the AXL network."""
    logger.info("Initializing Quant Process (Node A)...")
    axl_node = MockAXLNode(node_id="Quant_Node_A")
    last_market_id = 0
    last_feedback_id = 0
    last_execution_id = 0
    
    # Track proposal states for iteration
    # proposal_id -> {market_data, iteration, messages}
    proposal_history = {}
    
    logger.info("Quant listening for Market Data, Patriarch Feedback, and Execution Status...")
    
    while True:
        try:
            # 1. Listen for new market data
            market_messages = axl_node.subscribe(topic="MARKET_DATA", last_id=last_market_id)
            for msg in market_messages:
                last_market_id = msg["id"]
                market_data = msg["payload"]
                logger.info(f"Received new market data from {msg['sender']}. Analyzing...")
                
                state = {"market_data": market_data, "messages": [], "iteration": 0}
                result = quant_app.invoke(state)
                proposal: Proposal = result.get("current_proposal")
                
                if proposal:
                    if not proposal.proposal_id or proposal.proposal_id == "uuid_placeholder":
                        proposal.proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
                    
                    # Store state for potential iteration
                    proposal_history[proposal.proposal_id] = {
                        "market_data": market_data,
                        "iteration": result.get("iteration", 1),
                        "messages": result.get("messages", [])
                    }
                    
                    logger.info(f"Publishing Proposal {proposal.proposal_id} to AXL Network...")
                    axl_node.publish(topic="PROPOSALS", payload=proposal.model_dump())
                else:
                    logger.info("No actionable trade identified.")

            # 2. Listen for feedback from the Patriarch (Rejections)
            feedback_messages = axl_node.subscribe(topic="PROPOSAL_EVALUATIONS", last_id=last_feedback_id)
            for msg in feedback_messages:
                last_feedback_id = msg["id"]
                evaluation = msg["payload"]
                
                if evaluation["consensus_status"] == ConsensusStatus.REJECTED.value:
                    prop_id = evaluation["proposal_id"]
                    logger.warning(f"Quant received REJECTION for {prop_id}. Rationale: {evaluation['rationale']}")
                    
                    if prop_id in proposal_history:
                        history = proposal_history[prop_id]
                        if history["iteration"] < 3: # Limit iterations
                            logger.info(f"Iterating on proposal {prop_id} based on Patriarch feedback...")
                            
                            state = {
                                "market_data": history["market_data"],
                                "messages": history["messages"],
                                "iteration": history["iteration"],
                                "patriarch_feedback": evaluation["rationale"]
                            }
                            
                            result = quant_app.invoke(state)
                            new_proposal: Proposal = result.get("current_proposal")
                            
                            if new_proposal:
                                # Update history with new proposal ID (or keep same)
                                # For clarity, we'll give it a new ID or suffix
                                new_proposal.proposal_id = f"{prop_id}_v{history['iteration']+1}"
                                
                                proposal_history[new_proposal.proposal_id] = {
                                    "market_data": history["market_data"],
                                    "iteration": result.get("iteration", history["iteration"] + 1),
                                    "messages": result.get("messages", [])
                                }
                                
                                logger.info(f"Publishing REVISED Proposal {new_proposal.proposal_id} to AXL Network...")
                                axl_node.publish(topic="PROPOSALS", payload=new_proposal.model_dump())
                            else:
                                logger.info("Quant conceded after feedback. No revised proposal.")
                        else:
                            logger.error(f"Max iterations reached for {prop_id}. Stopping negotiation.")

            time.sleep(2) # Polling interval
            
        except KeyboardInterrupt:
            logger.info("Quant Process shutting down.")
            break
        except Exception as e:
            logger.error(f"Error in Quant daemon: {e}")
            time.sleep(5)

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
         logger.error("CRITICAL: OPENAI_API_KEY environment variable is not set.")
         exit(1)
         
    run_quant_daemon()