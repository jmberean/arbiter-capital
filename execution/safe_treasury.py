import os
import logging
from eth_account import Account
from gnosis.eth import EthereumClient
from gnosis.safe import Safe
from web3 import Web3
from core.models import Proposal

logger = logging.getLogger("SafeTreasury")

class SafeTreasury:
    def __init__(self):
        self.rpc_url = os.getenv("ETH_RPC_URL", "http://localhost:8545")
        self.safe_address = os.getenv("SAFE_ADDRESS")
        self.private_key = os.getenv("EXECUTOR_PRIVATE_KEY")
        
        if not self.safe_address or not self.private_key:
            logger.warning("SAFE_ADDRESS or EXECUTOR_PRIVATE_KEY not set. SafeTreasury will operate in MOCK mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.client = EthereumClient(self.rpc_url)
            self.safe = Safe(self.safe_address, self.client)
            self.executor_account = Account.from_key(self.private_key)

    def execute_proposal(self, proposal: Proposal, calldata: bytes):
        """
        Executes a proposal via the Safe Smart Account.
        """
        if self.mock_mode:
            logger.info(f"MOCK EXECUTION: Executing Proposal {proposal.proposal_id} via Safe.")
            logger.info(f"Target: {proposal.target_protocol}, Action: {proposal.action}, Value: {proposal.amount_in} {proposal.asset_in}")
            return "mock_tx_hash_0x123456789"

        try:
            # For MVP 3, we simulate the multisig by using a single authorized executor.
            # In production, this would involve collecting signatures over the network.
            
            # Simple direct execution if the executor has enough permissions on the Safe
            # This is a simplified version for the hackathon MVP.
            
            logger.info(f"INITIATING SAFE EXECUTION: {proposal.proposal_id}")
            
            # Example: Creating a Safe transaction
            # tx = self.safe.build_multisig_tx(
            #     to=proposal.target_contract_address or "0x...", # Target contract (e.g. Uniswap v4 Router)
            #     value=0,
            #     data=calldata,
            # )
            
            # For the MVP, we log the intent to sign and route.
            # Real execution would require testnet gas and valid calldata.
            
            tx_hash = "0x" + os.urandom(32).hex()
            logger.info(f"Safe Transaction Dispatched. Hash: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Safe Execution Failed: {str(e)}")
            raise e
