import os
import json
import time
import hashlib
import logging
import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryManager")

# Mock 0G storage path
ZERO_G_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "0g_storage")

class MemoryManager:
    def __init__(self):
        os.makedirs(ZERO_G_STORAGE_PATH, exist_ok=True)
        
        # Initialize ChromaDB client
        db_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
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
        Mocks writing the immutable decision receipt to the 0G Layer 1 Data Availability Testnet.
        Returns a mock block hash.
        """
        receipt_str = json.dumps(decision_receipt, sort_keys=True)
        # Generate a fake block hash
        zero_g_hash = hashlib.sha256(receipt_str.encode('utf-8')).hexdigest()
        
        # Write to "0G" storage
        file_path = os.path.join(ZERO_G_STORAGE_PATH, f"{zero_g_hash}.json")
        with open(file_path, "w") as f:
            f.write(receipt_str)
            
        logger.info(f"Permanently written to 0G Testnet. Block Hash: {zero_g_hash}")
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
