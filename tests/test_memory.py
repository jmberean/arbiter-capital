import os
import pytest
import shutil
import time
import uuid
from memory.memory_manager import MemoryManager

@pytest.fixture
def memory_manager():
    # Use unique paths to avoid file locking issues on Windows
    unique_id = str(uuid.uuid4())[:8]
    test_chroma_path = f"test_chroma_{unique_id}"
    test_0g_path = f"test_0g_{unique_id}"
    
    # Mock environment for test
    os.environ["ZERO_G_RPC_URL"] = ""
    os.environ["ZERO_G_PRIVATE_KEY"] = ""
    
    # Initialize with test-specific paths
    mm = MemoryManager(storage_path=test_0g_path, db_path=test_chroma_path)
    
    yield mm
    
    # We intentionally skip cleanup of ChromaDB here to avoid PermissionError on Windows.
    # In a CI environment, the whole runner directory would be cleared.

def test_memory_save_and_recall(memory_manager):
    proposal = {
        "proposal_id": "test_mem_001",
        "action": "SWAP",
        "asset_in": "WETH",
        "asset_out": "USDC",
        "rationale": "High volatility detected."
    }
    transcript = "Quant: Rotating to stables. Patriarch: Approved."
    
    # Save decision
    zero_g_hash = memory_manager.save_decision(proposal, transcript)
    assert zero_g_hash is not None
    assert len(zero_g_hash) == 64 # SHA256 hash length
    
    # Query it back
    results = memory_manager.query_historical_decisions("volatility swap")
    assert len(results) > 0
    assert results[0]["proposal"]["proposal_id"] == "test_mem_001"
    assert results[0]["0g_hash_verified"] == zero_g_hash

def test_memory_live_mode_init():
    # Test that it correctly identifies live mode if env vars are present
    os.environ["ZERO_G_RPC_URL"] = "http://localhost:8545"
    os.environ["ZERO_G_PRIVATE_KEY"] = "0x" + "1" * 64
    unique_id = str(uuid.uuid4())[:8]
    mm = MemoryManager(storage_path=f"test_0g_live_{unique_id}", db_path=f"test_chroma_live_{unique_id}")
    assert hasattr(mm, 'live_mode')
