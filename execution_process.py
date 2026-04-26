import time
import logging
import json
import os
from dotenv import load_dotenv
from core.network import MockAXLNode
from core.models import Proposal
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ExecutionProcess")

def run_execution_daemon():
    """Runs Process 3 (Execution Node) as a continuous listener for FIREWALL_CLEARED events."""
    logger.info("Initializing Execution Process (Process 3 - Deterministic)...")
    
    # Initialize components
    axl_node = MockAXLNode(node_id="Execution_Node_P3")
    treasury = SafeTreasury()
    router = UniswapV4Router()
    last_processed_id = 0
    
    logger.info("Execution Node listening for FIREWALL_CLEARED events...")
    
    while True:
        try:
            # 1. Listen for proposals that passed the firewall
            cleared_proposals = axl_node.subscribe(topic="FIREWALL_CLEARED", last_id=last_processed_id)
            
            for msg in cleared_proposals:
                last_processed_id = msg["id"]
                proposal_dict = msg["payload"]
                proposal = Proposal(**proposal_dict)
                
                logger.info(f"🚀 RECEIVED AUTHORIZED PROPOSAL: {proposal.proposal_id}")
                
                # 2. Generate Uniswap v4 Calldata
                calldata = router.generate_calldata(proposal)
                
                # 3. Execute via Safe Smart Account
                tx_hash = treasury.execute_proposal(proposal, calldata)
                
                logger.info(f"✅ EXECUTION COMPLETE for {proposal.proposal_id}. Tx Hash: {tx_hash}")
                
                # 4. Notify the network of successful execution
                axl_node.publish(topic="EXECUTION_SUCCESS", payload={
                    "proposal_id": proposal.proposal_id,
                    "tx_hash": tx_hash,
                    "timestamp": time.time()
                })
                
            time.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("Execution Process shutting down.")
            break
        except Exception as e:
            logger.error(f"Error in Execution daemon: {e}")
            time.sleep(5)

if __name__ == "__main__":
    load_dotenv()
    run_execution_daemon()
