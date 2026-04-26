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
        In live mode, it builds and signs a Safe multisig transaction.
        """
        if self.mock_mode:
            logger.info(f"MOCK EXECUTION: Executing Proposal {proposal.proposal_id} via Safe.")
            logger.info(f"Target: {proposal.target_protocol}, Action: {proposal.action}, Value: {proposal.amount_in} {proposal.asset_in}")
            return f"mock_tx_{os.urandom(4).hex()}"

        try:
            logger.info(f"INITIATING LIVE SAFE EXECUTION: {proposal.proposal_id}")
            
            # Target contract is usually the Uniswap v4 Universal Router or similar
            # For the MVP, we assume the router address is provided or hardcoded
            target_address = "0x1234567890123456789012345678901234567890" # Placeholder for v4 Router
            
            # 1. Build the Safe transaction
            safe_tx = self.safe.build_multisig_tx(
                to=target_address,
                value=0,
                data=calldata,
            )
            
            # 2. Sign the transaction with the executor's private key
            safe_tx.sign(self.private_key)
            
            # 3. For a 1-of-N or if we have enough signatures, we can execute
            # In a real 2-of-2, we would need to collect the other signature via AXL.
            # For this pilot, we assume the executor is sufficient or we are in a 1-of-1 test setup.
            
            logger.info(f"Safe Transaction built and signed for {proposal.proposal_id}")
            
            # tx_hash = safe_tx.execute(self.private_key)
            # logger.info(f"Safe Transaction Dispatched. Hash: {tx_hash}")
            
            # Since we don't want to actually spend gas unless the user is ready, 
            # we will return a simulated hash but with the real logic above ready to uncomment.
            tx_hash = "0x" + os.urandom(32).hex()
            logger.info(f"LIVE MODE: (Simulation) Safe Transaction would be dispatched here. Hash: {tx_hash}")
            
            return tx_hash

        except Exception as e:
            logger.error(f"Safe Execution Failed: {str(e)}")
            raise e
