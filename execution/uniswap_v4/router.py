import os
import logging
from eth_abi import encode
from eth_utils import keccak
from web3 import Web3
from core.models import Proposal, ActionType
from execution.uniswap_v4.universal_router import (
    CMD_V4_SWAP,
    CMD_PERMIT2_PERMIT,
    build_v4_swap_input,
    build_ur_execute_calldata,
)
from execution.uniswap_v4.permit2 import ensure_permit2_approval

logger = logging.getLogger("UniswapV4Router")

# Sepolia token addresses — override via env for testnet pinning
WETH_SEPOLIA  = os.getenv("WETH_SEPOLIA",  "0xfFf9976782d46CC05630D1f6eBab18b2324d6B14")
USDC_SEPOLIA  = os.getenv("USDC_SEPOLIA",  "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
STETH_SEPOLIA = os.getenv("STETH_SEPOLIA", "0x3e3FE7dBc6B4C189E7128855dD526361c49b40Af")
WBTC_SEPOLIA  = os.getenv("WBTC_SEPOLIA",  "0x29f2D40B0605204364af54EC677bD022dA425d03")

ASSET_MAP: dict[str, str] = {
    "WETH":  WETH_SEPOLIA,
    "USDC":  USDC_SEPOLIA,
    "stETH": STETH_SEPOLIA,
    "WBTC":  WBTC_SEPOLIA,
}

# Lido submit(address referral) for stETH minting
LIDO_SUBMIT_SELECTOR = keccak(text="submit(address)")[:4]

# Exported so tests can verify without hardcoding magic bytes
SWAP_SELECTOR = CMD_V4_SWAP  # single-byte command; full calldata selector is UR_EXEC_SELECTOR


class UniswapV4Router:
    """Generates Universal Router calldata for Uniswap v4 interactions."""

    def __init__(self, w3: Web3 | None = None, owner: str | None = None):
        self.w3 = w3
        self.owner = owner

    def _get_pool_key(self, proposal: Proposal) -> tuple:
        addr0 = ASSET_MAP.get(proposal.asset_in, WETH_SEPOLIA)
        addr1 = ASSET_MAP.get(proposal.asset_out or "USDC", USDC_SEPOLIA)

        # Canonical ordering required by PoolManager
        if int(addr0, 16) > int(addr1, 16):
            addr0, addr1 = addr1, addr0

        hook_addr = (
            os.getenv("ARBITER_THROTTLE_HOOK", "0x0000000000000000000000000000000000000000")
            if proposal.v4_hook_required and proposal.v4_hook_required.lower() not in ("false", "none", "0", "")
            else "0x0000000000000000000000000000000000000000"
        )
        return (addr0, addr1, 3000, 60, hook_addr)  # 0.3% fee, tickSpacing=60

    def generate_calldata(self, proposal: Proposal) -> bytes:
        if proposal.action == ActionType.SWAP:
            return self._encode_swap(proposal)
        elif proposal.action == ActionType.STAKE_LST:
            return self._encode_lido_submit(proposal)
        elif proposal.action == ActionType.EMERGENCY_WITHDRAW:
            return self._encode_emergency_withdraw(proposal)
        else:
            logger.warning("Calldata generation for %s not implemented.", proposal.action)
            return b"\x00" * 4

    def _encode_emergency_withdraw(self, proposal: Proposal) -> bytes:
        """Encodes an ERC20 transfer(owner, amount) as a mock emergency exit."""
        if not self.owner:
            logger.warning("No owner set for emergency withdraw, returning null")
            return b"\x00" * 4
        
        # selector for transfer(address,uint256)
        selector = keccak(text="transfer(address,uint256)")[:4]
        amount = int(proposal.amount_in_units or "0")
        encoded = encode(["address", "uint256"], [self.owner, amount])
        
        logger.info("Generated EMERGENCY_WITHDRAW (Transfer) calldata for %s: %s units to %s",
                    proposal.asset_in, amount, self.owner)
        return selector + encoded

    def _encode_swap(self, proposal: Proposal) -> bytes:
        if proposal.amount_in_units is None:
            raise ValueError(f"Proposal {proposal.proposal_id} missing amount_in_units")

        pool_key = self._get_pool_key(proposal)
        asset_in_addr = ASSET_MAP.get(proposal.asset_in, WETH_SEPOLIA)
        zero_for_one = int(pool_key[0], 16) == int(asset_in_addr, 16)

        amount_in = int(proposal.amount_in_units)
        v4_input = build_v4_swap_input(pool_key, zero_for_one, amount_in)

        ur_addr = os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x" + "0" * 40)
        needs_permit, permit_input = ensure_permit2_approval(
            token=asset_in_addr,
            amount_units=amount_in,
            spender=ur_addr,
            owner=self.owner,
            w3=self.w3,
            deadline=proposal.deadline_unix,
        )

        if needs_permit:
            commands = CMD_PERMIT2_PERMIT + CMD_V4_SWAP
            inputs = [permit_input, v4_input]
        else:
            commands = CMD_V4_SWAP
            inputs = [v4_input]

        deadline = proposal.deadline_unix
        calldata = build_ur_execute_calldata(commands, inputs, deadline)
        logger.info("Generated UR SWAP calldata: %s → %s (%s units), permit=%s",
                    proposal.asset_in, proposal.asset_out, proposal.amount_in_units, needs_permit)
        return calldata

    def _encode_lido_submit(self, proposal: Proposal) -> bytes:
        """Encodes Lido submit(address referral) to mint stETH."""
        if proposal.amount_in_units is None:
            raise ValueError(f"Proposal {proposal.proposal_id} missing amount_in_units")
        referral = "0x0000000000000000000000000000000000000000"
        encoded = encode(["address"], [referral])
        logger.info("Generated Lido SUBMIT calldata: %s units ETH", proposal.amount_in_units)
        return LIDO_SUBMIT_SELECTOR + encoded
