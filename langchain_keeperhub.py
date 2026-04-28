"""
LangChain bridge for KeeperHub MCP. Exposes KeeperHub as reusable LangChain tools
for any LangGraph project — not just Arbiter Capital.

Usage in any LangGraph agent:
    from langchain_keeperhub import KeeperHubSimulateTool, KeeperHubExecuteTool
    tools = [KeeperHubSimulateTool(), KeeperHubExecuteTool()]
    agent = create_react_agent(llm, tools)

Configuration via env:
    KEEPERHUB_SERVER_PATH    - path to the KeeperHub MCP server binary/script
    SAFE_ADDRESS             - the Safe to operate on
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Optional, Type

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class _SimulateInput(BaseModel):
    to: str = Field(..., description="Target contract address (checksummed hex).")
    value: int = Field(0, description="Wei to send.")
    data_hex: str = Field(..., description="Calldata hex (with or without 0x prefix).")
    operation: int = Field(0, description="0=CALL, 1=DELEGATECALL.")


class _ExecuteInput(_SimulateInput):
    signatures_hex: str = Field(..., description="Concatenated Safe-format owner signatures (hex).")


# ---------------------------------------------------------------------------
# MCP transport helper
# ---------------------------------------------------------------------------

async def _mcp_call(tool_name: str, args: dict) -> dict:
    server_path = os.environ.get("KEEPERHUB_SERVER_PATH")
    if not server_path:
        # Mock path: return a plausible success response for dev/testing
        if tool_name == "simulate_safe_tx":
            return {"success": True, "gas_used": 120000, "return_data": "0x",
                    "revert_reason": None, "fork_block": 0, "simulator_signature": "0x" + "00" * 65}
        return {"tx_hash": f"mock_tx_{os.urandom(4).hex()}"}

    params = StdioServerParameters(command="node", args=[server_path], env=os.environ.copy())
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

    def _run(self, to: str, value: int = 0, data_hex: str = "0x", operation: int = 0) -> str:
        return json.dumps(asyncio.run(self._arun(to=to, value=value, data_hex=data_hex, operation=operation)))

    async def _arun(self, to: str, value: int = 0, data_hex: str = "0x", operation: int = 0) -> dict:
        return await _mcp_call("simulate_safe_tx", {
            "safe_address": os.environ.get("SAFE_ADDRESS", ""),
            "to": to,
            "value": value,
            "data": data_hex if data_hex.startswith("0x") else "0x" + data_hex,
            "operation": operation,
        })


class KeeperHubExecuteTool(BaseTool):
    name: str = "keeperhub_execute_safe_transaction"
    description: str = (
        "Broadcast a fully-signed Safe transaction via KeeperHub's reliable execution layer. "
        "Caller must have already collected the required threshold of owner signatures."
    )
    args_schema: Type[BaseModel] = _ExecuteInput

    def _run(self, to: str, value: int = 0, data_hex: str = "0x",
             operation: int = 0, signatures_hex: str = "") -> str:
        return json.dumps(asyncio.run(self._arun(
            to=to, value=value, data_hex=data_hex,
            operation=operation, signatures_hex=signatures_hex,
        )))

    async def _arun(self, to: str, value: int = 0, data_hex: str = "0x",
                    operation: int = 0, signatures_hex: str = "") -> dict:
        return await _mcp_call("execute_safe_transaction", {
            "safe_address": os.environ.get("SAFE_ADDRESS", ""),
            "to": to,
            "value": value,
            "data": data_hex if data_hex.startswith("0x") else "0x" + data_hex,
            "operation": operation,
            "signatures": signatures_hex,
        })
