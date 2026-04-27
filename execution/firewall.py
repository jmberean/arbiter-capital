import json
import logging
import os
from core.models import Proposal, ConsensusStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolicyFirewall")

# Hardcoded Constraints
WHITELISTED_ASSETS = {"WETH", "USDC", "stETH", "WBTC", "PT-USDC", "SOL"}
ALLOWED_PROTOCOLS = {"Uniswap_V4", "Lido", "Pendle"}
ALLOWED_HOOKS = {
    os.getenv("V4_HOOK_VOL_ORACLE"),
    os.getenv("V4_HOOK_DYNAMIC_FEE"),
    os.getenv("ARBITER_THROTTLE_HOOK"),
    "0x0000000000000000000000000000000000000000",
}
MAX_TRANSACTION_VALUE_USD = 50000.0
MAX_DAILY_DRAWDOWN_BPS = 500
MAX_GAS_PRICE_GWEI = 500
MIN_PROPOSAL_DEADLINE_SECONDS = 60

class MarketOracle:
    """Simple Oracle for the firewall to verify transaction values."""
    def __init__(self):
        self.prices = {
            "WETH": 3500.0,
            "USDC": 1.0,
            "SOL": 150.0,
            "WBTC": 65000.0,
            "stETH": 3510.0,
            "PT-USDC": 0.92
        }

    def get_price(self, asset: str) -> float:
        return self.prices.get(asset, 0.0)

class PolicyFirewall:
    def __init__(self):
        self.oracle = MarketOracle()

    def _get_usd_value(self, asset: str, amount_units: str) -> float:
        """Calculate approximate USD value from base units."""
        price = self.oracle.get_price(asset)
        if price == 0.0: return float('inf')
        
        # simplified decimal conversion
        from core.models import DECIMALS_BY_SYMBOL
        decimals = DECIMALS_BY_SYMBOL.get(asset, 18)
        amount = float(amount_units) / (10 ** decimals)
        return price * amount

    def validate_hook_address(self, hook_addr: str, expected_flags: int) -> bool:
        """Bit-level permission validation for v4 hooks."""
        if not hook_addr or hook_addr == "0x0000000000000000000000000000000000000000":
            return True
        addr_int = int(hook_addr, 16)
        # v4 hooks encode permissions in the bottom 14 bits
        return (addr_int & 0x3FFF) & expected_flags == expected_flags

    def validate_proposal(self, proposal: Proposal) -> bool:
        """
        Validates a Proposal against strict institutional constraints.
        """
        logger.info(f"Validating Proposal ID: {proposal.proposal_id}")

        if proposal.consensus_status != ConsensusStatus.ACCEPTED:
            raise ValueError(f"Proposal must be ACCEPTED. Current: {proposal.consensus_status}")

        if proposal.target_protocol not in ALLOWED_PROTOCOLS:
            raise ValueError(f"Constraint Violation: Target protocol {proposal.target_protocol} not allowed.")

        if proposal.asset_in not in WHITELISTED_ASSETS:
            raise ValueError(f"Constraint Violation: Asset In '{proposal.asset_in}' is not whitelisted.")
        
        if proposal.asset_out and proposal.asset_out not in WHITELISTED_ASSETS:
             raise ValueError(f"Constraint Violation: Asset Out '{proposal.asset_out}' is not whitelisted.")

        usd_value = self._get_usd_value(proposal.asset_in, proposal.amount_in_units)
        if usd_value > MAX_TRANSACTION_VALUE_USD:
            raise ValueError(f"Constraint Violation: Transaction value (${usd_value:,.2f}) exceeds max (${MAX_TRANSACTION_VALUE_USD:,.2f}).")

        # Hook validation
        if proposal.v4_hook_required and proposal.v4_hook_required not in ALLOWED_HOOKS:
             raise ValueError(f"Constraint Violation: Hook {proposal.v4_hook_required} not in ALLOWED_HOOKS.")

        logger.info(f"Proposal {proposal.proposal_id} CLEARED Policy Firewall.")
        return True
