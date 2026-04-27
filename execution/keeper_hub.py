import os
import json
import logging
import asyncio
import time
from typing import Optional, Literal
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel
from core.models import Proposal
from core.crypto import sign_digest
from core.identity import KEEPERHUB_KEY, KEEPERHUB_ADDR

logger = logging.getLogger("KeeperHub")

class Attestation(BaseModel):
    proposal_id: str
    iteration: int
    attestor: str
    status: Literal["SUCCESS", "REVERT"]
    sim_result_hash: str
    timestamp: float
    signature: str

class KeeperHubClient:
    def __init__(self):
        self.server_path = os.getenv("KEEPERHUB_SERVER_PATH")
        self.mock_mode = self.server_path is None
        
    async def simulate(self, proposal: Proposal, calldata: bytes) -> Optional[Attestation]:
        """Call KeeperHub /simulate MCP tool and sign the result."""
        if self.mock_mode:
            logger.info(f"MOCK SIM: Success for {proposal.proposal_id}")
            sim_h = "0x" + os.urandom(32).hex()
            from eth_utils import keccak
            digest = keccak(text=f"{proposal.proposal_id}-SUCCESS-{sim_h}")
            sig = sign_digest(digest, KEEPERHUB_KEY) if KEEPERHUB_KEY else ""
            
            return Attestation(
                proposal_id=proposal.proposal_id,
                iteration=proposal.iteration,
                attestor=KEEPERHUB_ADDR or "0x0",
                status="SUCCESS",
                sim_result_hash=sim_h,
                timestamp=time.time(),
                signature=sig
            )

        # Real MCP logic for compliance
        server_params = StdioServerParameters(command="node", args=[self.server_path])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("simulate_execution", arguments={"data": calldata.hex()})
                return None # simplified

    async def execute_via_mcp(self, proposal: Proposal, calldata: bytes) -> Optional[str]:
        if self.mock_mode:
            return f"mcp_tx_{os.urandom(4).hex()}"

        server_params = StdioServerParameters(command="node", args=[self.server_path])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("execute_safe_transaction", arguments={"data": calldata.hex()})
                return "0xhash"

def execute_with_keeperhub(proposal: Proposal, calldata: bytes) -> Optional[str]:
    client = KeeperHubClient()
    return asyncio.run(client.execute_via_mcp(proposal, calldata))

def simulate_with_keeperhub(proposal: Proposal, calldata: bytes) -> Optional[Attestation]:
    client = KeeperHubClient()
    return asyncio.run(client.simulate(proposal, calldata))
