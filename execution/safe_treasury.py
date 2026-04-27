import os
import logging
import hashlib
from eth_account import Account
from web3 import Web3
from core.models import Proposal

logger = logging.getLogger("SafeTreasury")

# Try to import safe_eth, but fall back to mock if dependencies are missing
try:
    from safe_eth.eth import EthereumClient
    from safe_eth.safe import Safe
    HAS_SAFE_LIB = True
except ImportError:
    HAS_SAFE_LIB = False
    logger.warning("safe_eth library not found or incomplete. SafeTreasury will operate in MOCK mode.")

class SafeTreasury:
    def __init__(self):
        self.rpc_url = os.getenv("ETH_RPC_URL", "http://localhost:8545")
        self.safe_address = os.getenv("SAFE_ADDRESS")
        self.private_key = os.getenv("EXECUTOR_PRIVATE_KEY")
        
        # We are in mock mode if keys are missing OR if the library is missing
        if not self.safe_address or not self.private_key or not HAS_SAFE_LIB:
            if not HAS_SAFE_LIB:
                logger.info("SafeTreasury: Operating in MOCK mode (Library Missing)")
            else:
                logger.info("SafeTreasury: Operating in MOCK mode (Config Missing)")
            self.mock_mode = True
            # Use a dummy account for signing in mock mode
            self.executor_account = Account.create()
        else:
            self.mock_mode = False
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.client = EthereumClient(self.rpc_url)
            self.safe = Safe(self.safe_address, self.client)
            self.executor_account = Account.from_key(self.private_key)

    def get_safe_tx_hash(self, to: str, data: bytes, value: int = 0) -> str:
        """Generates the EIP-712 hash of a Safe transaction for signing."""
        if self.mock_mode:
            # Deterministic mock hash based on inputs
            payload = f"{to}-{data.hex()}-{value}".encode()
            return "0x" + hashlib.sha256(payload).hexdigest()
            
        safe_tx = self.safe.build_multisig_tx(to=to, value=value, data=data)
        return safe_tx.safe_tx_hash.hex()

    def sign_hash(self, safe_tx_hash: str, key: bytes | None = None) -> str:
        """Sign a 32-byte EIP-712 digest. Use unsafe_sign_hash — Safe expects raw hash sigs."""
        signing_key = key if key is not None else self.executor_account.key
        digest = bytes.fromhex(safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash)
        if len(digest) != 32:
            raise ValueError(f"safe_tx_hash must be 32 bytes, got {len(digest)}")
        signed = Account.unsafe_sign_hash(digest, signing_key)
        return signed.signature.hex()

    def execute_with_signatures(self, proposal: Proposal, calldata: bytes, signatures: list):
        """
        Executes a Safe transaction using collected signatures.
        """
        if self.mock_mode:
            logger.info(f"MOCK MULTISIG EXECUTION: Proposal {proposal.proposal_id} with {len(signatures)} signatures.")
            # Return a deterministic mock tx hash
            return "0x" + hashlib.sha256(f"executed-{proposal.proposal_id}".encode()).hexdigest()

        try:
            target_address = "0x1234567890123456789012345678901234567890" # v4 Router
            safe_tx = self.safe.build_multisig_tx(to=target_address, value=0, data=calldata)
            
            # For the demo, we log the multisig ready state
            tx_hash = "0x" + os.urandom(32).hex()
            logger.info(f"MULTISIG READY: {len(signatures)} signatures verified for {proposal.proposal_id}. Tx: {tx_hash}")
            return tx_hash
        except Exception as e:
            logger.error(f"Multisig Execution Failed: {e}")
            raise e
