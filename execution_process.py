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

from core.crypto import recover_signer
from core.identity import SAFE_OWNERS
from core.dedupe import DedupeLedger

def run_execution_daemon():
    """Runs Process 3 (Execution Node) as a continuous listener for FIREWALL_CLEARED and signatures."""
    logger.info("Initializing Execution Process (Process 3 - Deterministic)...")
    
    # Initialize components
    axl_node = MockAXLNode(node_id="Execution_Node_P3", url_env="AXL_NODE_URL_EXEC")
    treasury = SafeTreasury()
    router = UniswapV4Router()
    dedupe = DedupeLedger()
    
    last_cleared_id = 0
    last_sig_id = 0
    THRESHOLD = int(os.getenv("CONSENSUS_THRESHOLD", "2"))
    
    # pending_proposals: proposal_id -> {proposal, signatures: [sig1, sig2...]}
    pending_proposals = {}
    
    logger.info(f"Execution Node listening (Threshold: {THRESHOLD})...")
    
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
                
                if sig_data.signature not in pending_proposals[prop_id]["signatures"]:
                    pending_proposals[prop_id]["signatures"].append(sig_data.signature)
                    logger.info(f"Collected signature for {prop_id}. Total: {len(pending_proposals[prop_id]['signatures'])}")

            # 2. Listen for proposals that passed the firewall
            cleared_proposals = axl_node.subscribe(topic="FIREWALL_CLEARED", last_id=last_cleared_id)
            for msg in cleared_proposals:
                last_cleared_id = msg["id"]
                proposal = Proposal(**msg["payload"])
                
                if proposal.proposal_id not in pending_proposals:
                    pending_proposals[proposal.proposal_id] = {"proposal": None, "signatures": []}
                
                pending_proposals[proposal.proposal_id]["proposal"] = proposal
                logger.info(f"Confirmed Firewall clearance for {proposal.proposal_id}.")

            # 3. Check for ready transactions
            for prop_id, data in list(pending_proposals.items()):
                proposal: Proposal = data["proposal"]
                sigs = data["signatures"]
                
                if proposal and proposal.safe_tx_hash:
                    safe_h = bytes.fromhex(proposal.safe_tx_hash[2:])
                    seen = set()
                    valid_sigs = []
                    for s in sigs:
                        addr = recover_signer(safe_h, s)
                        if addr in SAFE_OWNERS and addr not in seen:
                            seen.add(addr)
                            valid_sigs.append(s)
                    
                    if len(seen) >= THRESHOLD:
                        logger.info(f"🚀 MULTISIG THRESHOLD MET for {prop_id} by {seen}. Proceeding to execution.")
                        
                        if dedupe.already_executed(treasury.safe_address or "0x0", proposal.safe_nonce or 0):
                            logger.warning(f"Nonce {proposal.safe_nonce} already used. Skipping.")
                            del pending_proposals[prop_id]
                            continue

                        # 4. Generate Uniswap v4 Calldata
                        calldata = router.generate_calldata(proposal)
                        
                        # Build Safe-format signatures (sorted by address ascending)
                        sorted_signers = sorted(list(seen), key=lambda a: int(a, 16))
                        sigs_blob = ""
                        for addr in sorted_signers:
                            sig = next(s for s in valid_sigs if recover_signer(safe_h, s) == addr)
                            sigs_blob += sig[2:]

                        # 5. Execute
                        tx_hash = treasury.execute_with_signatures(proposal, calldata, [sigs_blob])
                        
                        if tx_hash:
                            logger.info(f"✅ EXECUTION COMPLETE for {prop_id}. Tx Hash: {tx_hash}")
                            dedupe.mark(treasury.safe_address or "0x0", proposal.safe_nonce or 0, prop_id, tx_hash)
                            axl_node.publish(topic="EXECUTION_SUCCESS", payload={"proposal_id": prop_id, "tx_hash": tx_hash})
                            del pending_proposals[prop_id]

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
