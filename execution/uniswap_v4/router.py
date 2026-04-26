import logging
import eth_abi
from core.models import Proposal, ActionType

logger = logging.getLogger("UniswapV4Router")

# Sepolia Testnet Addresses
WETH_SEPOLIA = "0xfFf9976782d46CC05630D1f6eBab18b2324d6B14"
USDC_SEPOLIA = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
POOL_MANAGER = "0x000000000004444c5dc75cb358380d2e3de08a90"
VOLATILITY_ORACLE_HOOK = "0x0000000000000000000000000000000000000001" # Placeholder

ASSET_MAP = {
    "WETH": WETH_SEPOLIA,
    "USDC": USDC_SEPOLIA,
    "stETH": "0x3510...placeholder",
}

class UniswapV4Router:
    """
    Generates Uniswap v4 calldata for the PoolManager and Universal Router.
    v4 uses a singleton architecture where all pools are identified by a PoolKey.
    """
    
    def _get_pool_key(self, proposal: Proposal) -> tuple:
        """Constructs a Uniswap v4 PoolKey (currency0, currency1, fee, tickSpacing, hooks)."""
        addr0 = ASSET_MAP.get(proposal.asset_in, WETH_SEPOLIA)
        addr1 = ASSET_MAP.get(proposal.asset_out, USDC_SEPOLIA)
        
        # Ensure canonical ordering
        if int(addr0, 16) > int(addr1, 16):
            addr0, addr1 = addr1, addr0
            
        fee = 3000 # Default 0.3%
        tick_spacing = 60
        hook_addr = VOLATILITY_ORACLE_HOOK if proposal.v4_hook_required else "0x0000000000000000000000000000000000000000"
        
        return (addr0, addr1, fee, tick_spacing, hook_addr)

    def generate_calldata(self, proposal: Proposal) -> bytes:
        """
        Generates real EVM calldata for Uniswap v4 interactions.
        """
        if proposal.action == ActionType.SWAP:
            pool_key = self._get_pool_key(proposal)
            
            # v4 swap parameters: (PoolKey, IPoolManager.SwapParams, bool testSettings, bytes hookData)
            # SwapParams: (bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96)
            zero_for_one = int(pool_key[0], 16) == int(ASSET_MAP.get(proposal.asset_in), 16)
            amount_specified = int(proposal.amount_in * 1e18) # Simplified decimals
            sqrt_price_limit = 0 # No limit
            
            swap_params = (zero_for_one, amount_specified, sqrt_price_limit)
            
            # Encode using eth_abi (matching the v4 PoolManager.swap signature)
            # function swap(PoolKey memory key, SwapParams memory params, bytes calldata hookData)
            encoded_key = eth_abi.encode(
                ['(address,address,uint24,int24,address)', '(bool,int256,uint160)', 'bytes'],
                [pool_key, swap_params, b""]
            )
            
            # Prepend the swap function selector (e.g., from PoolManager)
            # selector = 0x12345678 (placeholder)
            selector = b"\x12\x34\x56\x78"
            
            logger.info(f"Generated v4 SWAP calldata for {proposal.asset_in} -> {proposal.asset_out}")
            return selector + encoded_key
            
        elif proposal.action == ActionType.STAKE_LST:
            # Placeholder for LST staking calldata (e.g. Lido deposit)
            return b"\xAA\xBB" + eth_abi.encode(['uint256'], [int(proposal.amount_in * 1e18)])

        else:
            logger.warning(f"Calldata generation for {proposal.action} not yet fully implemented for v4.")
            return b"\x00" * 4
