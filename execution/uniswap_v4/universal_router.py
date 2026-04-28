"""
Uniswap Universal Router calldata builder.
Encodes V4_SWAP (and optional PERMIT2_PERMIT) commands for execute(bytes,bytes[],uint256).
"""
import time
from eth_abi import encode
from eth_utils import keccak

CMD_V4_SWAP        = bytes([0x10])
CMD_PERMIT2_PERMIT = bytes([0x0A])

# execute(bytes commands, bytes[] inputs, uint256 deadline)
_UR_EXEC_SIG = "execute(bytes,bytes[],uint256)"
UR_EXEC_SELECTOR = keccak(text=_UR_EXEC_SIG)[:4]

MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

DEFAULT_DEADLINE_SECONDS = 300  # 5 minutes


def build_v4_swap_input(
    pool_key: tuple,
    zero_for_one: bool,
    amount_specified: int,
    sqrt_price_limit: int = 0,
    hook_data: bytes = b"",
) -> bytes:
    """
    Encodes the bytes input for a CMD_V4_SWAP command.

    amount_specified: negative = exact-input swap (use -int(amount_in_units))
    sqrt_price_limit: 0 means use MIN/MAX based on direction.
    """
    if sqrt_price_limit == 0:
        sqrt_price_limit = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1

    swap_params = (zero_for_one, amount_specified, sqrt_price_limit)
    return encode(
        ["(address,address,uint24,int24,address)", "(bool,int256,uint160)", "bytes"],
        [pool_key, swap_params, hook_data],
    )


def build_permit2_input(
    token: str,
    amount_units: int,
    expiration: int,
    nonce: int,
    spender: str,
    signature: bytes,
) -> bytes:
    """Encodes the bytes input for a CMD_PERMIT2_PERMIT command."""
    return encode(
        ["(address,uint160,uint48,uint48)", "address", "bytes"],
        [(token, amount_units, expiration, nonce), spender, signature],
    )


def build_ur_execute_calldata(
    commands: bytes,
    inputs: list[bytes],
    deadline: int | None = None,
) -> bytes:
    """Returns complete calldata for UniversalRouter.execute(...)."""
    if deadline is None:
        deadline = int(time.time()) + DEFAULT_DEADLINE_SECONDS
    body = encode(["bytes", "bytes[]", "uint256"], [commands, inputs, deadline])
    return UR_EXEC_SELECTOR + body
