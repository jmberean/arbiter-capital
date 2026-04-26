import os
import json
import time
import hashlib
import logging
import chromadb
from chromadb.utils import embedding_functions
from web3 import Web3
from eth_account import Account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryManager")

# Local backup/mock 0G storage path
ZERO_G_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "0g_storage")

class MemoryManager:
    def __init__(self):
        os.makedirs(ZERO_G_STORAGE_PATH, exist_ok=True)
        
        # Initialize 0G Layer 1 Connection
        self.zero_g_rpc = os.getenv("ZERO_G_RPC_URL")
        self.zero_g_private_key = os.getenv("ZERO_G_PRIVATE_KEY")
        self.chain_id = int(os.getenv("ZERO_G_CHAIN_ID", "16602"))
        
        if self.zero_g_rpc and self.zero_g_private_key and not self.zero_g_private_key.startswith("0xabc123"):
            try:
                self.w3 = Web3(Web3.HTTPProvider(self.zero_g_rpc))
                self.account = Account.from_key(self.zero_g_private_key)
                self.live_mode = True
                logger.info(f"0G Live Memory initialized. Account: {self.account.address}")
            except Exception as e:
                logger.error(f"Failed to initialize 0G Live Memory: {e}. Falling back to MOCK mode.")
                self.live_mode = False
        else:
            logger.warning("ZERO_G_RPC_URL or ZERO_G_PRIVATE_KEY missing/invalid. Memory will operate in MOCK mode.")
            self.live_mode = False

        # Initialize ChromaDB client with retry logic for concurrent process initialization
        db_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        # ... (rest of __init__ is unchanged)
        for attempt in range(5):
            try:
                self.chroma_client = chromadb.PersistentClient(path=db_path)
                break
            except Exception as e:
                logger.warning(f"ChromaDB init failed, retrying ({attempt+1}/5): {e}")
                time.sleep(1)
        else:
            self.chroma_client = chromadb.PersistentClient(path=db_path)
            
        # Use OpenAI embeddings for the Retrieval Layer
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="decision_receipts",
            embedding_function=openai_ef
        )

    def _write_to_0g(self, decision_receipt: dict) -> str:
        """
        Writes the immutable decision receipt to the 0G Layer 1 Data Availability Testnet.
        In live_mode, sends an EVM transaction with receipt data.
        In mock_mode, writes to a local JSON file.
        Returns the transaction hash or local hash.
        """
        receipt_str = json.dumps(decision_receipt, sort_keys=True)
        
        if self.live_mode:
            try:
                nonce = self.w3.eth.get_transaction_count(self.account.address)
                # Decision receipt as transaction data
                tx = {
                    'nonce': nonce,
                    'to': self.account.address, # Sending to self for audit trail
                    'value': 0,
                    'gas': 300000, # Base 21k + data cost
                    'gasPrice': self.w3.eth.gas_price,
                    'data': self.w3.to_hex(text=receipt_str),
                    'chainId': self.chain_id
                }
                
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.zero_g_private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
                
                logger.info(f"Permanently written to 0G Testnet. Tx Hash: {tx_hash}")
                
                # Still write to local storage as a cache/backup
                zero_g_hash = hashlib.sha256(receipt_str.encode('utf-8')).hexdigest()
                file_path = os.path.join(ZERO_G_STORAGE_PATH, f"{tx_hash}.json")
                with open(file_path, "w") as f:
                    f.write(receipt_str)
                
                return tx_hash
                
            except Exception as e:
                logger.error(f"Failed to write to 0G Testnet: {e}. Falling back to local hash.")
                # Fall through to mock logic if transaction fails

        # Mock/Fallback logic
        zero_g_hash = hashlib.sha256(receipt_str.encode('utf-8')).hexdigest()
        file_path = os.path.join(ZERO_G_STORAGE_PATH, f"{zero_g_hash}.json")
        with open(file_path, "w") as f:
            f.write(receipt_str)
            
        logger.info(f"Written to Local 0G Storage. Hash: {zero_g_hash}")
        return zero_g_hash

    def save_decision(self, proposal: dict, transcript: str):
        """Saves a decision receipt to 0G and indexes it in ChromaDB."""
        decision_receipt = {
            "timestamp": time.time(),
            "proposal": proposal,
            "transcript": transcript
        }
        
        # 1. Write to 0G (Base Layer)
        zero_g_hash = self._write_to_0g(decision_receipt)
        
        # 2. Index in ChromaDB (Retrieval Layer)
        doc_id = f"dec_{int(time.time())}"
        
        # We embed the rationale and the transcript to allow semantic search
        searchable_text = f"Action: {proposal.get('action')} {proposal.get('asset_in')} to {proposal.get('asset_out')}. Rationale: {proposal.get('rationale')}. Debate: {transcript}"
        
        self.collection.add(
            documents=[searchable_text],
            metadatas=[{"0g_hash": zero_g_hash, "proposal_id": proposal.get("proposal_id", "unknown")}],
            ids=[doc_id]
        )
        logger.info(f"Indexed decision {doc_id} in ChromaDB. Vector embeddings saved.")
        return zero_g_hash

    def query_historical_decisions(self, query_string: str, n_results: int = 2) -> list:
        """
        Tool for agents to search the Dual-Layer Memory.
        Queries ChromaDB for semantic matches, then retrieves the immutable receipt from 0G using the hash.
        """
        logger.info(f"Agent querying memory for: '{query_string}'")
        
        if self.collection.count() == 0:
            logger.info("ChromaDB is empty. No historical context available.")
            return []
            
        results = self.collection.query(
            query_texts=[query_string],
            n_results=min(n_results, self.collection.count())
        )
        
        historical_context = []
        for i, meta in enumerate(results['metadatas'][0]):
            zero_g_hash = meta["0g_hash"]
            # Retrieve from 0G base layer
            file_path = os.path.join(ZERO_G_STORAGE_PATH, f"{zero_g_hash}.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    receipt = json.load(f)
                    historical_context.append({
                        "0g_hash_verified": zero_g_hash,
                        "proposal": receipt["proposal"],
                        "relevance_score": results['distances'][0][i] if 'distances' in results and results['distances'] else None
                    })
                    
        return historical_context
