import logging
import os
import time
from core.models import Proposal, ConsensusStatus, DECIMALS_BY_SYMBOL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolicyFirewall")

# Hardcoded institutional constraints (not LLM-controllable).
WHITELISTED_ASSETS = {"WETH", "USDC", "stETH", "WBTC", "PT-USDC"}
ALLOWED_PROTOCOLS = {"Uniswap_V4", "Lido", "Pendle"}
ALLOWED_HOOKS = {
    os.getenv("V4_HOOK_VOL_ORACLE"),
    os.getenv("V4_HOOK_DYNAMIC_FEE"),
    os.getenv("ARBITER_THROTTLE_HOOK"),
    "0x0000000000000000000000000000000000000000",
}

MAX_TRANSACTION_VALUE_USD = float(os.getenv("MAX_TRANSACTION_VALUE_USD", "50000"))
MAX_DAILY_DRAWDOWN_BPS = int(os.getenv("MAX_DAILY_DRAWDOWN_BPS", "500"))          # 5%
MAX_PER_ASSET_ALLOCATION_BPS = int(os.getenv("MAX_PER_ASSET_ALLOCATION_BPS", "5000"))  # 50%
MAX_GAS_PRICE_GWEI = int(os.getenv("MAX_GAS_PRICE_GWEI", "500"))
MIN_PROPOSAL_DEADLINE_SECONDS = int(os.getenv("MIN_PROPOSAL_DEADLINE_SECONDS", "60"))

# Bottom 14 bits of an Uniswap v4 hook address encode permission flags.
# ArbiterThrottleHook needs BEFORE_SWAP_FLAG | AFTER_SWAP_FLAG.
HOOK_BEFORE_SWAP_FLAG = 1 << 7   # 0x0080
HOOK_AFTER_SWAP_FLAG  = 1 << 6   # 0x0040
ARBITER_THROTTLE_REQUIRED_FLAGS = HOOK_BEFORE_SWAP_FLAG | HOOK_AFTER_SWAP_FLAG


class MarketOracle:
    """Simple Oracle for the firewall to verify transaction values."""

    def __init__(self):
        self.prices = {
            "WETH": 3500.0,
            "USDC": 1.0,
            "WBTC": 65000.0,
            "stETH": 3510.0,
            "PT-USDC": 0.92,
        }

    def get_price(self, asset: str) -> float:
        return self.prices.get(asset, 0.0)


class PolicyFirewall:
    def __init__(self):
        self.oracle = MarketOracle()

    def _get_usd_value(self, asset: str, amount_units: str) -> float:
        price = self.oracle.get_price(asset)
        if price == 0.0:
            return float("inf")
        decimals = DECIMALS_BY_SYMBOL.get(asset, 18)
        amount = float(amount_units) / (10 ** decimals)
        return price * amount

    def validate_hook_address(self, hook_addr: str, expected_flags: int) -> bool:
        """Bit-level permission validation for Uniswap v4 hooks.
        Returns True for the zero address (no hook) or if all required flag
        bits are set on the bottom 14 bits of `hook_addr`."""
        if not hook_addr or hook_addr == "0x0000000000000000000000000000000000000000":
            return True
        try:
            addr_int = int(hook_addr, 16)
        except ValueError:
            return False
        return (addr_int & 0x3FFF) & expected_flags == expected_flags

    def validate_proposal(self, proposal: Proposal) -> bool:
        """Validates a Proposal against strict institutional constraints.
        Raises ValueError on any violation. Returns True only on full pass.
        """
        logger.info(f"Validating Proposal ID: {proposal.proposal_id}")

        # 1. Consensus status
        if proposal.consensus_status != ConsensusStatus.ACCEPTED:
            raise ValueError(f"Proposal must be ACCEPTED. Current: {proposal.consensus_status}")

        # 2. Protocol whitelist
        if proposal.target_protocol not in ALLOWED_PROTOCOLS:
            raise ValueError(
                f"Constraint Violation: Target protocol must be one of {ALLOWED_PROTOCOLS}. "
                f"Got: {proposal.target_protocol}"
            )

        # 3. Asset whitelist
        if proposal.asset_in not in WHITELISTED_ASSETS:
            raise ValueError(f"Constraint Violation: Asset In '{proposal.asset_in}' is not whitelisted.")

        if proposal.asset_out and proposal.asset_out not in WHITELISTED_ASSETS:
            raise ValueError(f"Constraint Violation: Asset Out '{proposal.asset_out}' is not whitelisted.")

        # 4. Transaction value cap
        usd_value = self._get_usd_value(proposal.asset_in, proposal.amount_in_units or "0")
        if usd_value > MAX_TRANSACTION_VALUE_USD:
            raise ValueError(
                f"Constraint Violation: Transaction value (${usd_value:,.2f}) "
                f"exceeds maximum allowed (${MAX_TRANSACTION_VALUE_USD:,.2f})."
            )

        # 5. Risk score cap (10000 bps == 100%)
        if proposal.risk_score_bps is not None and proposal.risk_score_bps > 8000:
            raise ValueError(
                f"Constraint Violation: risk_score_bps={proposal.risk_score_bps} > 8000 ceiling."
            )

        # 6. Deadline sanity
        if proposal.deadline_unix is not None:
            now = int(time.time())
            if proposal.deadline_unix <= now:
                raise ValueError(
                    f"Constraint Violation: deadline_unix={proposal.deadline_unix} is in the past."
                )
            if proposal.deadline_unix - now < MIN_PROPOSAL_DEADLINE_SECONDS:
                raise ValueError(
                    f"Constraint Violation: deadline_unix gives only "
                    f"{proposal.deadline_unix - now}s — minimum is {MIN_PROPOSAL_DEADLINE_SECONDS}s."
                )

        # 7. Hook permission validation
        if proposal.v4_hook_required and proposal.v4_hook_required not in ALLOWED_HOOKS:
            raise ValueError(
                f"Constraint Violation: Hook {proposal.v4_hook_required} not in ALLOWED_HOOKS."
            )

        if proposal.v4_hook_required:
            arbiter_throttle = os.getenv("ARBITER_THROTTLE_HOOK", "")
            if arbiter_throttle and proposal.v4_hook_required.lower() == arbiter_throttle.lower():
                if not self.validate_hook_address(
                    proposal.v4_hook_required, ARBITER_THROTTLE_REQUIRED_FLAGS
                ):
                    raise ValueError(
                        f"Constraint Violation: ArbiterThrottleHook address "
                        f"{proposal.v4_hook_required} missing BEFORE_SWAP|AFTER_SWAP flag bits."
                    )

        logger.info(f"Proposal {proposal.proposal_id} CLEARED Policy Firewall.")
        return True
