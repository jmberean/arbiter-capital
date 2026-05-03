"""
LangChain bridge for KeeperHub MCP. Exposes KeeperHub as reusable LangChain tools
for any LangGraph project — not just Arbiter Capital.

Usage in any LangGraph agent:
    from langchain_keeperhub import KeeperHubSimulateTool, KeeperHubExecuteTool
    tools = [KeeperHubSimulateTool(), KeeperHubExecuteTool()]
    agent = create_react_agent(llm, tools)

Configuration via env:
    KEEPERHUB_SERVER_PATH    - path to the KeeperHub MCP server (*.py or *.js)
    SAFE_ADDRESS             - the Safe to operate on
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Optional, Type

from langchain_core.tools import BaseTool

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    ClientSession = None  # type: ignore
    StdioServerParameters = None  # type: ignore
    stdio_client = None  # type: ignore
    HAS_MCP = False

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class _SimulateInput(BaseModel):
    to: str = Field(..., description="Target contract address (checksummed hex).")
    value: int = Field(0, description="Wei to send.")
    data_hex: str = Field(..., description="Calldata hex (with or without 0x prefix).")
    operation: int = Field(0, description="0=CALL, 1=DELEGATECALL.")
    proposal_id: str = Field("mock", description="Proposal ID for attestor digest.")
    iteration: int = Field(0, description="Proposal iteration for attestor digest.")


class _ExecuteInput(_SimulateInput):
    signatures_hex: str = Field(..., description="Concatenated Safe-format owner signatures (hex).")


# ---------------------------------------------------------------------------
# MCP transport helper
# ---------------------------------------------------------------------------

def _server_command(server_path: str) -> tuple[str, list[str]]:
    """Return (command, args) to launch the MCP server."""
    if server_path.endswith(".py"):
        return sys.executable, [server_path]
    return "node", [server_path]


def _mock_simulate(args: dict) -> dict:
    """Dev-mode mock: signs with KEEPERHUB_ATTESTOR_KEY if set, else returns zero sig."""
    sim = {
        "success": True,
        "gas_used": 120_000,
        "return_data": "0x",
        "revert_reason": None,
        "fork_block": 0,
    }
    key_hex = os.environ.get("KEEPERHUB_ATTESTOR_KEY", "")
    if key_hex and not key_hex.startswith("0xabc") and key_hex != "0x" + "0" * 64:
        try:
            from core.crypto import sim_result_digest, sign_digest
            digest = sim_result_digest(
                proposal_id=args.get("proposal_id", "mock"),
                iteration=args.get("iteration", 0),
                success=True,
                gas_used=sim["gas_used"],
                return_data=sim["return_data"],
                fork_block=sim["fork_block"],
            )
            key_bytes = bytes.fromhex(key_hex[2:] if key_hex.startswith("0x") else key_hex)
            sim["simulator_signature"] = "0x" + sign_digest(digest, key_bytes)
        except Exception:
            sim["simulator_signature"] = "0x" + "00" * 65
    else:
        sim["simulator_signature"] = "0x" + "00" * 65
    return sim


async def _mcp_call(tool_name: str, args: dict) -> dict:
    server_path = os.environ.get("KEEPERHUB_SERVER_PATH")
    if not server_path or not HAS_MCP:
        if tool_name == "simulate_safe_tx":
            return _mock_simulate(args)
        return {"tx_hash": f"mock_tx_{os.urandom(4).hex()}"}

    command, cmd_args = _server_command(server_path)
    params = StdioServerParameters(command=command, args=cmd_args, env=os.environ.copy())
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=args)
            if result is None or not result.content:
                raise RuntimeError(f"KeeperHub MCP returned empty response for {tool_name}")
            return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class KeeperHubSimulateTool(BaseTool):
    name: str = "keeperhub_simulate_safe_tx"
    description: str = (
        "Simulate a Safe transaction by forking the latest chain state via KeeperHub. "
        "Returns success / revert + return data. Use before paying gas to confirm the tx will succeed."
    )
    args_schema: Type[BaseModel] = _SimulateInput

    def _run(self, to: str, value: int = 0, data_hex: str = "0x", operation: int = 0,
             proposal_id: str = "mock", iteration: int = 0) -> str:
        return json.dumps(asyncio.run(self._arun(
            to=to, value=value, data_hex=data_hex, operation=operation,
            proposal_id=proposal_id, iteration=iteration,
        )))

    async def _arun(self, to: str, value: int = 0, data_hex: str = "0x", operation: int = 0,
                    proposal_id: str = "mock", iteration: int = 0) -> dict:
        return await _mcp_call("simulate_safe_tx", {
            "safe_address": os.environ.get("SAFE_ADDRESS", ""),
            "to": to,
            "value": value,
            "data": data_hex if data_hex.startswith("0x") else "0x" + data_hex,
            "operation": operation,
            "proposal_id": proposal_id,
            "iteration": iteration,
        })


class KeeperHubExecuteTool(BaseTool):
    name: str = "keeperhub_execute_safe_transaction"
    description: str = (
        "Broadcast a fully-signed Safe transaction via KeeperHub's reliable execution layer. "
        "Caller must have already collected the required threshold of owner signatures."
    )
    args_schema: Type[BaseModel] = _ExecuteInput

    def _run(self, to: str, value: int = 0, data_hex: str = "0x",
             operation: int = 0, signatures_hex: str = "",
             proposal_id: str = "mock", iteration: int = 0) -> str:
        return json.dumps(asyncio.run(self._arun(
            to=to, value=value, data_hex=data_hex,
            operation=operation, signatures_hex=signatures_hex,
        )))

    async def _arun(self, to: str, value: int = 0, data_hex: str = "0x",
                    operation: int = 0, signatures_hex: str = "",
                    proposal_id: str = "mock", iteration: int = 0) -> dict:
        return await _mcp_call("execute_safe_transaction", {
            "safe_address": os.environ.get("SAFE_ADDRESS", ""),
            "to": to,
            "value": value,
            "data": data_hex if data_hex.startswith("0x") else "0x" + data_hex,
            "operation": operation,
            "signatures": signatures_hex,
        })
