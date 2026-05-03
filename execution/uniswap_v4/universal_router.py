"""
Uniswap Universal Router calldata builder.
Encodes V4_SWAP (and optional PERMIT2_PERMIT) commands for execute(bytes,bytes[],uint256).
"""
from __future__ import annotations

import time
from eth_abi import encode
from eth_utils import keccak

CMD_V4_SWAP        = bytes([0x10])
CMD_PERMIT2_PERMIT = bytes([0x0A])

# execute(bytes commands, bytes[] inputs, uint256 deadline)
_UR_EXEC_SIG = "execute(bytes,bytes[],uint256)"
UR_EXEC_SELECTOR = keccak(text=_UR_EXEC_SIG)[:4]

DEFAULT_DEADLINE_SECONDS = 300  # 5 minutes

# V4 action codes (Actions.sol)
_ACT_SWAP_EXACT_IN_SINGLE = bytes([0x06])
_ACT_SETTLE_ALL           = bytes([0x0c])
_ACT_TAKE_ALL             = bytes([0x0f])


def build_v4_swap_input(
    pool_key: tuple,
    zero_for_one: bool,
    amount_in: int,          # positive uint128 — exact input amount
    amount_out_min: int = 0,
    hook_data: bytes = b"",
) -> bytes:
    """
    Encodes the bytes input for a CMD_V4_SWAP command using the correct
    V4Router Actions format: abi.encode(bytes actions, bytes[] params).

    Actions: SWAP_EXACT_IN_SINGLE (0x06) → SETTLE_ALL (0x0c) → TAKE_ALL (0x0f)
    """
    actions = _ACT_SWAP_EXACT_IN_SINGLE + _ACT_SETTLE_ALL + _ACT_TAKE_ALL

    # ExactInputSingleParams: (PoolKey, bool zeroForOne, uint128 amountIn,
    #                          uint128 amountOutMinimum, uint256 minHopPriceX36, bytes hookData)
    swap_param = encode(
        ["((address,address,uint24,int24,address),bool,uint128,uint128,uint256,bytes)"],
        [(pool_key, zero_for_one, amount_in, amount_out_min, 0, hook_data)],
    )

    # SETTLE_ALL: (Currency currency_in, uint256 maxAmount)
    currency_in = pool_key[0] if zero_for_one else pool_key[1]
    settle_param = encode(["address", "uint256"], [currency_in, amount_in])

    # TAKE_ALL: (Currency currency_out, uint256 minAmount)
    currency_out = pool_key[1] if zero_for_one else pool_key[0]
    take_param = encode(["address", "uint256"], [currency_out, amount_out_min])

    return encode(["bytes", "bytes[]"], [actions, [swap_param, settle_param, take_param]])


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
        ["((address,uint160,uint48,uint48),address,uint256)", "bytes"],
        [((token, amount_units, expiration, nonce), spender, expiration), signature],
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
