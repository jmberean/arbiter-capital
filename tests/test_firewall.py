import pytest
from execution.firewall import PolicyFirewall
from core.models import Proposal, ConsensusStatus, ActionType

@pytest.fixture
def firewall():
    return PolicyFirewall()

def test_firewall_clears_valid_proposal(firewall):
    proposal = Proposal(
        proposal_id="test_001",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        asset_out="USDC",
        amount_in=10.0, # $35,000
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test valid.",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    assert firewall.validate_proposal(proposal) is True

def test_firewall_rejects_pending_proposal(firewall):
    proposal = Proposal(
        proposal_id="test_002",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=10.0,
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test valid.",
        consensus_status=ConsensusStatus.PENDING # Should reject
    )
    with pytest.raises(ValueError, match="must be ACCEPTED"):
        firewall.validate_proposal(proposal)

def test_firewall_rejects_high_value(firewall):
    proposal = Proposal(
        proposal_id="test_003",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=20.0, # 20 * 3500 = 70,000 > 50,000
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test high value.",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    with pytest.raises(ValueError, match="exceeds maximum allowed"):
        firewall.validate_proposal(proposal)

def test_firewall_rejects_invalid_protocol(firewall):
    proposal = Proposal(
        proposal_id="test_004",
        target_protocol="Uniswap_V3", # Invalid
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=10.0,
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test invalid protocol.",
        consensus_status=ConsensusStatus.ACCEPTED
    )
    with pytest.raises(ValueError, match="Target protocol must be"):
        firewall.validate_proposal(proposal)
