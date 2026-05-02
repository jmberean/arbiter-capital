#!/usr/bin/env python
"""
KeeperHub MCP Server — simulate_safe_tx + execute_safe_transaction.

Started as a subprocess (stdio transport) by langchain_keeperhub.py.
Signs simulation results with KEEPERHUB_ATTESTOR_KEY so consult_sim_oracle
can verify the attestation against the registered attestor address.

Run manually to test:
    python scripts/keeperhub_mcp_server.py

Or set KEEPERHUB_SERVER_PATH=scripts/keeperhub_mcp_server.py and let
langchain_keeperhub.py start it automatically.
"""
import asyncio
import json
import os
import sys

# Ensure repo root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eth_account import Account
from eth_utils import keccak
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ATTESTOR_KEY_HEX = os.environ.get("KEEPERHUB_ATTESTOR_KEY", "")
_RPC_URL = os.environ.get("ETH_RPC_URL") or os.environ.get("SEPOLIA_RPC", "")


def _load_key() -> bytes | None:
    v = _ATTESTOR_KEY_HEX
    if not v or v.startswith("0xabc") or v == "0x" + "0" * 64:
        return None
    return bytes.fromhex(v[2:] if v.startswith("0x") else v)


def _sim_result_digest(proposal_id: str, iteration: int, success: bool,
                       gas_used: int, return_data: str, fork_block: int) -> bytes:
    """Must match core/crypto.py::sim_result_digest exactly."""
    canonical = json.dumps({
        "proposal_id": proposal_id,
        "iteration": int(iteration),
        "success": bool(success),
        "gas_used": int(gas_used),
        "return_data": return_data or "0x",
        "fork_block": int(fork_block),
    }, sort_keys=True, separators=(",", ":")).encode()
    return keccak(canonical)


def _sign(digest_bytes: bytes, key_bytes: bytes) -> str:
    return "0x" + Account.unsafe_sign_hash(digest_bytes, key_bytes).signature.hex()


def _simulate(safe_address: str, to: str, value: int, data: str) -> dict:
    fork_block = 0
    success = True
    gas_used = 120_000
    return_data = "0x"
    revert_reason = None

    try:
        if _RPC_URL:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(_RPC_URL))
            fork_block = w3.eth.block_number
            result = w3.eth.call({
                "from": Web3.to_checksum_address(safe_address),
                "to": Web3.to_checksum_address(to),
                "value": value,
                "data": data,
            })
            return_data = "0x" + result.hex() if result else "0x"
    except Exception as exc:
        success = False
        revert_reason = str(exc)[:200]

    return {
        "success": success,
        "gas_used": gas_used,
        "return_data": return_data,
        "revert_reason": revert_reason,
        "fork_block": fork_block,
    }


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("keeperhub-sim-oracle")


@mcp.tool()
def simulate_safe_tx(
    safe_address: str,
    to: str,
    value: int = 0,
    data: str = "0x",
    operation: int = 0,
    proposal_id: str = "mock",
    iteration: int = 0,
) -> str:
    """Simulate a Safe transaction and return a signed attestation result."""
    sim = _simulate(safe_address, to, value, data)

    key = _load_key()
    if key:
        digest = _sim_result_digest(
            proposal_id=proposal_id,
            iteration=iteration,
            success=sim["success"],
            gas_used=sim["gas_used"],
            return_data=sim["return_data"],
            fork_block=sim["fork_block"],
        )
        sim["simulator_signature"] = _sign(digest, key)
    else:
        sim["simulator_signature"] = "0x" + "00" * 65

    return json.dumps(sim)


@mcp.tool()
def execute_safe_transaction(
    safe_address: str,
    to: str,
    value: int = 0,
    data: str = "0x",
    operation: int = 0,
    signatures: str = "0x",
) -> str:
    """Broadcast a fully-signed Safe transaction (demo: returns mock tx hash)."""
    import os as _os
    return json.dumps({"tx_hash": "0x" + _os.urandom(32).hex(), "status": "submitted"})


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
