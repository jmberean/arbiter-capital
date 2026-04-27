import pytest
import unittest.mock as mock
import sys
import os

# Mock the safe_eth module before it's imported by SafeTreasury
sys.modules["safe_eth"] = mock.MagicMock()
sys.modules["safe_eth.eth"] = mock.MagicMock()
sys.modules["safe_eth.safe"] = mock.MagicMock()

from core.models import Proposal, ActionType, ConsensusStatus
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router
from execution.keeper_hub import KeeperHubClient

def test_v4_router_calldata():
    router = UniswapV4Router()
    proposal = Proposal(
        proposal_id="exec_001",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        asset_out="USDC",
        amount_in=1.0,
        projected_apy=0.0,
        risk_score_evaluation=1.0,
        rationale="test",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    
    calldata = router.generate_calldata(proposal)
    assert isinstance(calldata, bytes)
    assert len(calldata) > 4
    assert calldata.startswith(b"\x12\x34\x56\x78")

def test_safe_treasury_mock():
    # Force mock mode for testing
    os.environ["SAFE_ADDRESS"] = "" 
    treasury = SafeTreasury()
    proposal = Proposal(
        proposal_id="exec_002",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=1.0,
        projected_apy=0.0,
        risk_score_evaluation=1.0,
        rationale="test",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    
    tx_hash = treasury.execute_with_signatures(proposal, b"0xdata", ["sig1"])
    assert tx_hash.startswith("0x")

def test_keeper_hub_mock():
    client = KeeperHubClient()
    proposal = Proposal(
        proposal_id="exec_003",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=1.0,
        projected_apy=0.0,
        risk_score_evaluation=1.0,
        rationale="test",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    
    # execute_via_mcp is async
    import asyncio
    tx_hash = asyncio.run(client.execute_via_mcp(proposal, b"0xdata"))
    assert tx_hash.startswith("mcp_tx_")
