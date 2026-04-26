import os
import json
import logging
import asyncio
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from core.models import Proposal

logger = logging.getLogger("KeeperHub")

class KeeperHubClient:
    """
    Client for interacting with the KeeperHub MCP server.
    KeeperHub acts as a deterministic execution delegate for the Safe treasury.
    """
    def __init__(self):
        self.server_path = os.getenv("KEEPERHUB_SERVER_PATH") # e.g. "path/to/keeperhub-server"
        self.mock_mode = self.server_path is None
        
        if self.mock_mode:
            logger.warning("KEEPERHUB_SERVER_PATH not set. KeeperHub will operate in MOCK mode.")

    async def execute_via_mcp(self, proposal: Proposal, calldata: bytes) -> Optional[str]:
        """
        Routes the validated proposal to KeeperHub via MCP for execution.
        """
        if self.mock_mode:
            logger.info(f"MOCK MCP: Routing Proposal {proposal.proposal_id} to KeeperHub.")
            return f"mcp_tx_{os.urandom(4).hex()}"

        try:
            # Configure MCP server parameters
            server_params = StdioServerParameters(
                command="node",
                args=[self.server_path],
                env=os.environ.copy()
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Call the 'execute_safe_transaction' tool on the KeeperHub MCP server
                    result = await session.call_tool("execute_safe_transaction", arguments={
                        "proposal_id": proposal.proposal_id,
                        "to": "0x1234567890123456789012345678901234567890", # v4 Router
                        "data": calldata.hex(),
                        "value": "0"
                    })
                    
                    if result and hasattr(result, "content"):
                         logger.info(f"KeeperHub MCP Execution Success: {result.content}")
                         # Extract tx_hash from result content if available
                         return "0x" + os.urandom(32).hex() # Placeholder for real hash from MCP
                    else:
                         logger.error(f"KeeperHub MCP Execution Failed: {result}")
                         return None

        except Exception as e:
            logger.error(f"Error communicating with KeeperHub MCP: {e}")
            return None

def execute_with_keeperhub(proposal: Proposal, calldata: bytes) -> Optional[str]:
    """Synchronous wrapper for async MCP execution."""
    client = KeeperHubClient()
    return asyncio.run(client.execute_via_mcp(proposal, calldata))
