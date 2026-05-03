"""
Permit2 allowance checker and approval builder.
ensure_permit2_approval() returns (needs_permit, permit2_input_bytes).
Callers prepend CMD_PERMIT2_PERMIT to their command list when needs_permit is True.
"""
from __future__ import annotations

import os
import time
import logging
from web3 import Web3
from eth_utils import keccak
from execution.uniswap_v4.universal_router import build_permit2_input

logger = logging.getLogger("Permit2")

PERMIT2_ADDRESS = os.getenv("PERMIT2_ADDRESS", "0x000000000022D473030F116dDEE9F6B43aC78BA3")
PERMIT2_EXPIRY_SECONDS = 86400  # 24 h

# allowance(address owner, address token, address spender) → (uint160,uint48,uint48)
_ALLOWANCE_SIG = "allowance(address,address,address)"
_ALLOWANCE_SELECTOR = keccak(text=_ALLOWANCE_SIG)[:4]


def _read_permit2_allowance(w3: Web3, owner: str, token: str, spender: str) -> tuple[int, int, int]:
    """Returns (amount, expiration, nonce) from Permit2.allowance."""
    call_data = (
        _ALLOWANCE_SELECTOR
        + b"\x00" * 12 + bytes.fromhex(owner[2:])
        + b"\x00" * 12 + bytes.fromhex(token[2:])
        + b"\x00" * 12 + bytes.fromhex(spender[2:])
    )
    raw = w3.eth.call({"to": PERMIT2_ADDRESS, "data": call_data.hex()})
    # Returns (uint160 amount, uint48 expiration, uint48 nonce) packed in 3 × 32-byte slots
    amount     = int.from_bytes(raw[0:32],  "big")
    expiration = int.from_bytes(raw[32:64], "big")
    nonce      = int.from_bytes(raw[64:96], "big")
    return amount, expiration, nonce


def ensure_permit2_approval(
    token: str,
    amount_units: int,
    spender: str,
    owner: str | None = None,
    w3: Web3 | None = None,
    deadline: int | None = None,
) -> tuple[bool, bytes]:
    """
    Checks current Permit2 allowance and builds a PERMIT2_PERMIT input if needed.

    Returns:
        (needs_permit: bool, permit2_input: bytes)
        Callers should prepend CMD_PERMIT2_PERMIT and the returned bytes when needs_permit=True.
    """
    # Use the caller-supplied deadline so calldata is deterministic across
    # quant signing and execution submission. Fallback to 24h from now.
    expiry = deadline if deadline is not None else int(time.time()) + PERMIT2_EXPIRY_SECONDS

    if w3 is None or owner is None:
        logger.debug("Permit2: no w3/owner — requesting permit unconditionally")
        permit_input = build_permit2_input(token, amount_units, expiry, 0, spender, b"")
        return True, permit_input

    try:
        current_amount, current_expiration, nonce = _read_permit2_allowance(w3, owner, token, spender)
        sufficient = (
            current_amount >= amount_units
            and current_expiration > int(time.time()) + 60
        )
        if sufficient:
            logger.debug("Permit2: allowance sufficient (amount=%d exp=%d)", current_amount, current_expiration)
            return False, b""

        permit_input = build_permit2_input(token, amount_units, expiry, nonce, spender, b"")
        logger.info("Permit2: building permit (token=%s amount=%d nonce=%d)", token, amount_units, nonce)
        return True, permit_input

    except Exception as e:
        logger.warning("Permit2 allowance check failed (%s) — requesting permit", e)
        permit_input = build_permit2_input(token, amount_units, expiry, 0, spender, b"")
        return True, permit_input
