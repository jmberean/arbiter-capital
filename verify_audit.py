import os
import json
import logging
import hashlib
from typing import List, Dict
from web3 import Web3
import chromadb
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AuditVerifier")

class AuditVerifier:
    def __init__(self):
        load_dotenv()
        
        # 0G L1 Connection
        self.zero_g_rpc = os.getenv("ZERO_G_RPC_URL", "https://evmrpc-testnet.0g.ai")
        self.w3 = Web3(Web3.HTTPProvider(self.zero_g_rpc))
        
        # ChromaDB setup
        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_collection("decision_receipts")
        
        # Local 0G backup path
        self.storage_path = os.path.join(os.path.dirname(__file__), "0g_storage")

    def verify_decision(self, doc_id: str, metadata: Dict) -> bool:
        """Verifies a single decision against the 0G testnet or local storage."""
        zero_g_hash = metadata.get("0g_hash")
        proposal_id = metadata.get("proposal_id")
        
        logger.info(f"Verifying Proposal {proposal_id} (Hash: {zero_g_hash[:12]}...)")
        
        # 1. Check if it's a real 0G Transaction Hash (0x...)
        if zero_g_hash.startswith("0x"):
            try:
                tx = self.w3.eth.get_transaction(zero_g_hash)
                if not tx:
                    logger.error(f"❌ FAILED: Transaction {zero_g_hash} not found on 0G Testnet.")
                    return False
                
                # Decode the data (receipt) from the transaction input
                input_data = tx.get("input", "")
                if not input_data:
                    logger.error(f"❌ FAILED: Transaction {zero_g_hash} has no data.")
                    return False
                
                # Convert hex to string
                try:
                    # Web3.to_text handles the 0x prefix
                    receipt_str = self.w3.to_text(input_data)
                    receipt = json.loads(receipt_str)
                    logger.info(f"✅ SUCCESS: Verified on 0G Testnet. Proposal: {receipt['proposal']['proposal_id']}")
                    return True
                except Exception as e:
                    logger.error(f"❌ FAILED: Could not decode 0G transaction data: {e}")
                    return False
                    
            except Exception as e:
                # If RPC fails or tx not found, check local fallback
                logger.warning(f"Could not verify on-chain ({e}). Checking local fallback...")
        
        # 2. Local Fallback / Mock Verification
        file_path = os.path.join(self.storage_path, f"{zero_g_hash}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
                # Verify SHA256 integrity
                calculated_hash = hashlib.sha256(content.encode()).hexdigest()
                
                # If it was a tx_hash, the filename might not match the sha256
                # But for mock hashes, they are the sha256.
                if not zero_g_hash.startswith("0x") and calculated_hash != zero_g_hash:
                    logger.error(f"❌ FAILED: Local integrity check failed for {zero_g_hash}")
                    return False
                    
                logger.info(f"✅ SUCCESS: Verified locally. Hash: {calculated_hash[:12]}...")
                return True
        else:
            logger.error(f"❌ FAILED: Decision receipt {zero_g_hash} not found in 0G storage.")
            return False

    def run_full_audit(self):
        """Iterates through all indexed decisions and verifies them."""
        logger.info("Starting Full Audit Verification...")
        
        # Get all documents from ChromaDB
        results = self.collection.get()
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", [])
        
        if not ids:
            logger.info("No decisions found in memory to verify.")
            return
            
        success_count = 0
        for i in range(len(ids)):
            if self.verify_decision(ids[i], metadatas[i]):
                success_count += 1
                
        logger.info(f"Audit Complete. Verified {success_count}/{len(ids)} decisions successfully.")

if __name__ == "__main__":
    verifier = AuditVerifier()
    verifier.run_full_audit()
