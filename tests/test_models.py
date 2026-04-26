import pytest
from pydantic import ValidationError
from core.models import Proposal, ConsensusStatus, ActionType

def test_valid_proposal():
    proposal = Proposal(
        proposal_id="prop_1",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        amount_in=10.0,
        projected_apy=5.0,
        risk_score_evaluation=4.0,
        rationale="Test rationale",
        consensus_status=ConsensusStatus.PENDING
    )
    assert proposal.proposal_id == "prop_1"
    assert proposal.risk_score_evaluation == 4.0

def test_invalid_risk_score():
    with pytest.raises(ValidationError):
        Proposal(
            proposal_id="prop_2",
            target_protocol="Uniswap_V4",
            action=ActionType.SWAP,
            asset_in="WETH",
            amount_in=10.0,
            projected_apy=5.0,
            risk_score_evaluation=11.0, # Invalid, > 10
            rationale="Test rationale"
        )
