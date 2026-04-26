import time
import logging
import json
import os
from dotenv import load_dotenv
from core.network import MockAXLNode
from core.models import Proposal, ConsensusMessage
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router
from execution.keeper_hub import execute_with_keeperhub

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ExecutionProcess")

def run_execution_daemon():
    """Runs Process 3 (Execution Node) as a continuous listener for FIREWALL_CLEARED and signatures."""
    logger.info("Initializing Execution Process (Process 3 - Deterministic)...")
    
    # Initialize components
    axl_node = MockAXLNode(node_id="Execution_Node_P3")
    treasury = SafeTreasury()
    router = UniswapV4Router()
    
    last_cleared_id = 0
    last_sig_id = 0
    
    # pending_proposals: proposal_id -> {proposal, signatures: [sig1, sig2...]}
    pending_proposals = {}
    
    logger.info("Execution Node listening for FIREWALL_CLEARED events and CONSENSUS_SIGNATURES...")
    
    while True:
        try:
            # 1. Listen for new signatures
            sig_messages = axl_node.subscribe(topic="CONSENSUS_SIGNATURES", last_id=last_sig_id)
            for msg in sig_messages:
                last_sig_id = msg["id"]
                sig_data = ConsensusMessage(**msg["payload"])
                
                prop_id = sig_data.proposal_id
                if prop_id not in pending_proposals:
                    pending_proposals[prop_id] = {"proposal": None, "signatures": []}
                
                # Deduplicate signatures from the same agent (simplified)
                if sig_data.signature not in pending_proposals[prop_id]["signatures"]:
                    pending_proposals[prop_id]["signatures"].append(sig_data.signature)
                    logger.info(f"Collected signature from {sig_data.signer_id} for {prop_id}. Total: {len(pending_proposals[prop_id]['signatures'])}")

            # 2. Listen for proposals that passed the firewall
            cleared_proposals = axl_node.subscribe(topic="FIREWALL_CLEARED", last_id=last_cleared_id)
            for msg in cleared_proposals:
                last_cleared_id = msg["id"]
                proposal = Proposal(**msg["payload"])
                
                if proposal.proposal_id not in pending_proposals:
                    pending_proposals[proposal.proposal_id] = {"proposal": None, "signatures": []}
                
                pending_proposals[proposal.proposal_id]["proposal"] = proposal
                logger.info(f"Confirmed Firewall clearance for {proposal.proposal_id}.")

            # 3. Check for ready transactions (Threshold = 1 for pilot, 2 for prod)
            # In this demo, if we have the Patriarch's signature, we are ready.
            for prop_id, data in list(pending_proposals.items()):
                proposal = data["proposal"]
                sigs = data["signatures"]
                
                if proposal and len(sigs) >= 1:
                    logger.info(f"🚀 MULTISIG THRESHOLD MET for {prop_id}. Proceeding to execution.")
                    
                    # 4. Generate Uniswap v4 Calldata
                    calldata = router.generate_calldata(proposal)
                    
                    # 5. Execute via KeeperHub (Preferred) or direct SafeTreasury
                    if os.getenv("KEEPERHUB_SERVER_PATH"):
                        logger.info("Attempting execution via KeeperHub MCP...")
                        tx_hash = execute_with_keeperhub(proposal, calldata)
                    else:
                        logger.info("KeeperHub not configured. Using direct SafeTreasury multisig execution...")
                        tx_hash = treasury.execute_with_signatures(proposal, calldata, sigs)
                    
                    if tx_hash:
                        logger.info(f"✅ EXECUTION COMPLETE for {prop_id}. Tx Hash: {tx_hash}")
                        # Notify network
                        axl_node.publish(topic="EXECUTION_SUCCESS", payload={
                            "proposal_id": prop_id,
                            "tx_hash": tx_hash,
                            "timestamp": time.time()
                        })
                        # Remove from pending
                        del pending_proposals[prop_id]
                    else:
                        logger.error(f"❌ EXECUTION FAILED for {prop_id}")

            time.sleep(2)
                
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
