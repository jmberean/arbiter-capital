"""KeeperHub MCP integration — Sim Oracle (P4) and execution facade.

The Sim Oracle wraps a KeeperHub `simulate_safe_tx` tool call, signs the
canonical SimulationResult digest with the attestor key, and returns an
Attestation that can be verified by Patriarch via core.identity.is_attestor.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Optional, Literal

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    ClientSession = None  # type: ignore
    StdioServerParameters = None  # type: ignore
    stdio_client = None  # type: ignore
    HAS_MCP = False

from pydantic import BaseModel

from core.crypto import sim_result_digest, sign_digest
from core.identity import KEEPERHUB_KEY, KEEPERHUB_ADDR
from core.models import Proposal, SimulationResult

logger = logging.getLogger("KeeperHub")


class Attestation(BaseModel):
    """Compatibility wrapper used by patriarch_process — carries the
    attestor-signed SimulationResult outcome in a single object."""
    proposal_id: str
    iteration: int
    attestor: str
    status: Literal["SUCCESS", "REVERT"]
    sim_result_hash: str
    timestamp: float
    signature: str


class KeeperHubClient:
    """MCP client for KeeperHub. Mocks responses when KEEPERHUB_SERVER_PATH is unset."""

    def __init__(self):
        self.server_path = os.getenv("KEEPERHUB_SERVER_PATH")
        self.mock_mode = self.server_path is None or not HAS_MCP
        self.safe_address = os.getenv("SAFE_ADDRESS", "0x" + "0" * 40)
        if self.server_path and not HAS_MCP:
            logger.warning("KEEPERHUB_SERVER_PATH set but `mcp` package not installed — falling back to MOCK mode.")

    def _server_command(self) -> tuple[str, list[str]]:
        import sys as _sys
        if self.server_path and self.server_path.endswith(".py"):
            return _sys.executable, [self.server_path]
        return "node", [self.server_path]

    # ------------------------------------------------------------------
    # simulate_safe_tx
    # ------------------------------------------------------------------
    async def simulate(self, proposal: Proposal, calldata: bytes) -> Optional[Attestation]:
        sim_data = await self._simulate_raw(proposal, calldata)
        if sim_data is None:
            return None

        success = bool(sim_data.get("success", True))
        gas_used = int(sim_data.get("gas_used", 0))
        return_data = sim_data.get("return_data", "0x")
        fork_block = int(sim_data.get("fork_block", 0))
        revert_reason = sim_data.get("revert_reason")

        digest = sim_result_digest(
            proposal_id=proposal.proposal_id,
            iteration=proposal.iteration,
            success=success,
            gas_used=gas_used,
            return_data=return_data,
            fork_block=fork_block,
        )

        if KEEPERHUB_KEY:
            sig = sign_digest(digest, KEEPERHUB_KEY)
        else:
            logger.warning("KEEPERHUB_ATTESTOR_KEY not set — Sim Oracle output will be unsigned.")
            sig = "0x" + "00" * 65

        return Attestation(
            proposal_id=proposal.proposal_id,
            iteration=proposal.iteration,
            attestor=KEEPERHUB_ADDR or "0x" + "0" * 40,
            status="SUCCESS" if success else "REVERT",
            sim_result_hash="0x" + digest.hex(),
            timestamp=time.time(),
            signature=sig,
        )

    async def simulate_signed_result(self, proposal: Proposal, calldata: bytes) -> SimulationResult:
        """Returns a fully-formed, attestor-signed SimulationResult per spec §12."""
        sim_data = await self._simulate_raw(proposal, calldata) or {}
        success = bool(sim_data.get("success", True))
        gas_used = int(sim_data.get("gas_used", 0))
        return_data = sim_data.get("return_data", "0x")
        fork_block = int(sim_data.get("fork_block", 0))

        digest = sim_result_digest(
            proposal_id=proposal.proposal_id,
            iteration=proposal.iteration,
            success=success,
            gas_used=gas_used,
            return_data=return_data,
            fork_block=fork_block,
        )
        sig = sign_digest(digest, KEEPERHUB_KEY) if KEEPERHUB_KEY else "0x" + "00" * 65

        return SimulationResult(
            request_id=sim_data.get("request_id", f"req_{int(time.time()*1000)}"),
            proposal_id=proposal.proposal_id,
            success=success,
            gas_used=gas_used,
            return_data=return_data,
            revert_reason=sim_data.get("revert_reason"),
            fork_block=fork_block,
            simulator_signature=sig,
            attestor_address=KEEPERHUB_ADDR,
            timestamp=time.time(),
        )

    async def _simulate_raw(self, proposal: Proposal, calldata: bytes) -> Optional[dict]:
        if self.mock_mode:
            logger.info(f"MOCK SIM: success for {proposal.proposal_id}")
            return {
                "success": True,
                "gas_used": 120000,
                "return_data": "0x",
                "revert_reason": None,
                "fork_block": 0,
                "request_id": f"mock_req_{os.urandom(4).hex()}",
            }

        cmd, cmd_args = self._server_command()
        server_params = StdioServerParameters(
            command=cmd, args=cmd_args, env=os.environ.copy()
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "simulate_safe_tx",
                    arguments={
                        "safe_address": self.safe_address,
                        "to": os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x" + "0" * 40),
                        "value": 0,
                        "data": "0x" + calldata.hex(),
                        "operation": 0,
                    },
                )
                if result is None or not result.content:
                    logger.error("KeeperHub returned empty simulate_safe_tx response")
                    return None
                try:
                    return json.loads(result.content[0].text)
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Failed to parse KeeperHub sim response: {e}")
                    return None

    # ------------------------------------------------------------------
    # execute_safe_transaction
    # ------------------------------------------------------------------
    async def execute_via_mcp(
        self, proposal: Proposal, calldata: bytes, signatures_hex: str = ""
    ) -> Optional[str]:
        if self.mock_mode:
            return f"mcp_tx_{os.urandom(4).hex()}"

        cmd, cmd_args = self._server_command()
        server_params = StdioServerParameters(
            command=cmd, args=cmd_args, env=os.environ.copy()
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "execute_safe_transaction",
                    arguments={
                        "safe_address": self.safe_address,
                        "to": os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x" + "0" * 40),
                        "value": 0,
                        "data": "0x" + calldata.hex(),
                        "operation": 0,
                        "signatures": signatures_hex if signatures_hex.startswith("0x") else "0x" + signatures_hex,
                    },
                )
                if result is None or not result.content:
                    logger.error("KeeperHub returned empty execute response")
                    return None
                try:
                    body = json.loads(result.content[0].text)
                    return body.get("tx_hash")
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Failed to parse KeeperHub execute response: {e}")
                    return None


# Synchronous facades --------------------------------------------------------

def execute_with_keeperhub(proposal: Proposal, calldata: bytes, signatures_hex: str = "") -> Optional[str]:
    return asyncio.run(KeeperHubClient().execute_via_mcp(proposal, calldata, signatures_hex))


def simulate_with_keeperhub(proposal: Proposal, calldata: bytes) -> Optional[Attestation]:
    return asyncio.run(KeeperHubClient().simulate(proposal, calldata))


def simulate_signed_result(proposal: Proposal, calldata: bytes) -> SimulationResult:
    return asyncio.run(KeeperHubClient().simulate_signed_result(proposal, calldata))
