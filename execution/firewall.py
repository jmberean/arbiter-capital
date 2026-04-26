import json
import logging
from core.models import Proposal, ConsensusStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolicyFirewall")

# Hardcoded Constraints
WHITELISTED_ASSETS = ["WETH", "USDC", "SOL", "WBTC", "stETH", "PT-USDC", "LST"]
MAX_TRANSACTION_VALUE_USD = 50000.0
REQUIRED_ARCHITECTURE = "Uniswap_V4"

class MarketOracle:
    """Simple Oracle for the firewall to verify transaction values."""
    def __init__(self):
        # In a real system, this would fetch from a Chainlink feed or Exchange API
        self.prices = {
            "WETH": 3500.0,
            "USDC": 1.0,
            "SOL": 150.0,
            "WBTC": 65000.0,
            "stETH": 3510.0,
            "PT-USDC": 0.92,
            "LST": 3500.0
        }

    def get_price(self, asset: str) -> float:
        return self.prices.get(asset, 0.0)

class PolicyFirewall:
    def __init__(self):
        self.oracle = MarketOracle()

    def _get_usd_value(self, asset: str, amount: float) -> float:
        """Calculate approximate USD value of an asset."""
        price = self.oracle.get_price(asset)
        if price == 0.0:
            return float('inf') 
        return price * amount

    def validate_proposal(self, proposal: Proposal) -> bool:
        """
        Validates a Proposal against strict institutional constraints.
        Returns True if 'CLEARED', raises ValueError if constraints are violated.
        """
        logger.info(f"Validating Proposal ID: {proposal.proposal_id}")

        if proposal.consensus_status != ConsensusStatus.ACCEPTED:
            raise ValueError(f"Proposal {proposal.proposal_id} must be ACCEPTED by the Patriarch. Current status: {proposal.consensus_status}")

        if proposal.target_protocol != REQUIRED_ARCHITECTURE:
            raise ValueError(f"Constraint Violation: Target protocol must be {REQUIRED_ARCHITECTURE}. Got: {proposal.target_protocol}")

        if proposal.asset_in not in WHITELISTED_ASSETS:
            raise ValueError(f"Constraint Violation: Asset In '{proposal.asset_in}' is not whitelisted.")
        
        if proposal.asset_out and proposal.asset_out not in WHITELISTED_ASSETS:
             raise ValueError(f"Constraint Violation: Asset Out '{proposal.asset_out}' is not whitelisted.")

        usd_value = self._get_usd_value(proposal.asset_in, proposal.amount_in)
        if usd_value > MAX_TRANSACTION_VALUE_USD:
            raise ValueError(f"Constraint Violation: Transaction value (${usd_value:,.2f}) exceeds maximum allowed (${MAX_TRANSACTION_VALUE_USD:,.2f}).")

        logger.info(f"Proposal {proposal.proposal_id} CLEARED Policy Firewall.")
        return True

if __name__ == "__main__":
    # Test execution
    firewall = PolicyFirewall()
    
    # Valid proposal
    valid_proposal = Proposal(
        proposal_id="test_001",
        target_protocol="Uniswap_V4",
        action="SWAP",
        asset_in="WETH",
        asset_out="USDC",
        amount_in=10.0, # $35,000
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test valid.",
        consensus_status=ConsensusStatus.ACCEPTED
    )

    try:
        firewall.validate_proposal(valid_proposal)
    except Exception as e:
        logger.error(e)

    # Invalid proposal (Value too high)
    invalid_proposal = Proposal(
        proposal_id="test_002",
        target_protocol="Uniswap_V4",
        action="SWAP",
        asset_in="WETH",
        amount_in=20.0, # $70,000
        projected_apy=5.0,
        risk_score_evaluation=2.0,
        rationale="Test invalid value.",
        consensus_status=ConsensusStatus.ACCEPTED
    )

    try:
        firewall.validate_proposal(invalid_proposal)
    except Exception as e:
        logger.error(e)
