import os
import json
import time
import uuid
import hashlib
import logging
import chromadb
from typing import Optional, List, Dict
from chromadb.utils import embedding_functions
from eth_utils import keccak
from web3 import Web3
from eth_account import Account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryManager")

# Local backup/mock 0G storage path
ZERO_G_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "0g_storage")

class MemoryManager:
    def __init__(self, storage_path: Optional[str] = None, db_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "0g_storage")
        os.makedirs(self.storage_path, exist_ok=True)
        
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

        # Initialize ChromaDB client with retry logic
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        for attempt in range(5):
            try:
                self.chroma_client = chromadb.PersistentClient(path=self.db_path)
                break
            except Exception as e:
                logger.warning(f"ChromaDB init failed, retrying ({attempt+1}/5): {e}")
                time.sleep(1)
        else:
            self.chroma_client = chromadb.PersistentClient(path=self.db_path)
            
        # Use OpenAI embeddings for the Retrieval Layer
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="decision_receipts",
            embedding_function=openai_ef
        )

    def write_artifact(self, kind: str, payload: dict) -> str:
        """Generic write that hash-chains receipts and persists to 0G."""
        from memory.audit_chain import AuditChainHead
        head = AuditChainHead()
        receipt = {
            "schema_version": 5,
            "receipt_type": kind,
            "receipt_id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "prev_0g_tx_hash": head.head,
            "payload": payload,
        }
        canonical = json.dumps(
            {k: v for k, v in receipt.items() if k != "receipt_hash"},
            sort_keys=True, separators=(",", ":"),
        ).encode()
        receipt["receipt_hash"] = "0x" + keccak(canonical).hex()
        tx_hash = self._write_to_0g(receipt)
        head.advance(tx_hash)
        if kind in ("DecisionReceipt", "LLMContext", "NegotiationTranscript"):
            self._index_chroma(receipt, tx_hash)
        return tx_hash

    def _index_chroma(self, receipt: dict, tx_hash: str) -> None:
        kind = receipt["receipt_type"]
        payload = receipt.get("payload", {})
        if kind == "DecisionReceipt":
            proposal = payload.get("proposal", {})
            text = (
                f"Action: {proposal.get('action')} {proposal.get('asset_in')} "
                f"to {proposal.get('asset_out')}. Rationale: {proposal.get('rationale')}"
            )
        elif kind == "LLMContext":
            text = (
                f"Agent: {payload.get('invoking_agent')} "
                f"Model: {payload.get('model_id')} "
                f"Schema: {payload.get('structured_output_schema_name')}"
            )
        else:
            text = json.dumps(payload)[:500]
        doc_id = f"{kind}_{receipt['receipt_id']}"
        proposal_id = payload.get("proposal_id", payload.get("proposal", {}).get("proposal_id", "unknown"))
        self.collection.upsert(
            documents=[text],
            metadatas=[{"0g_hash": tx_hash, "proposal_id": proposal_id, "receipt_type": kind}],
            ids=[doc_id],
        )

    def read_artifact(self, tx_hash_or_local_hash: str) -> dict:
        """Retrieve an artifact from 0G storage (local or L1)."""
        file_path = os.path.join(self.storage_path, f"{tx_hash_or_local_hash}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        
        if self.live_mode:
            # In real 0G, we'd fetch the transaction data from the RPC
            try:
                tx = self.w3.eth.get_transaction(tx_hash_or_local_hash)
                data_text = self.w3.to_text(tx['input'])
                return json.loads(data_text)
            except Exception as e:
                logger.error(f"Failed to retrieve from 0G L1: {e}")
        
        raise FileNotFoundError(f"Artifact {tx_hash_or_local_hash} not found in storage.")

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
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
                
                logger.info(f"Permanently written to 0G Testnet. Tx Hash: {tx_hash}")
                
                # Still write to local storage as a cache/backup
                file_path = os.path.join(self.storage_path, f"{tx_hash}.json")
                with open(file_path, "w") as f:
                    f.write(receipt_str)
                
                return tx_hash
                
            except Exception as e:
                logger.error(f"Failed to write to 0G Testnet: {e}. Falling back to local hash.")

        # Mock/Fallback logic
        zero_g_hash = hashlib.sha256(receipt_str.encode('utf-8')).hexdigest()
        file_path = os.path.join(self.storage_path, f"{zero_g_hash}.json")
        with open(file_path, "w") as f:
            f.write(receipt_str)
            
        logger.info(f"Written to Local 0G Storage. Hash: {zero_g_hash}")
        return zero_g_hash

    def save_decision(self, proposal: dict, transcript: str) -> str:
        """Saves a decision receipt to the hash-chained 0G log and indexes in ChromaDB."""
        return self.write_artifact("DecisionReceipt", {"proposal": proposal, "transcript": transcript})

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
            file_path = os.path.join(self.storage_path, f"{zero_g_hash}.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    receipt = json.load(f)
                # Handle both v5 receipts (payload.proposal) and legacy flat receipts (proposal)
                payload = receipt.get("payload", receipt)
                proposal_data = payload.get("proposal", payload)
                historical_context.append({
                    "0g_hash_verified": zero_g_hash,
                    "proposal": proposal_data,
                    "relevance_score": (
                        results['distances'][0][i]
                        if 'distances' in results and results['distances']
                        else None
                    ),
                })
                    
        return historical_context
