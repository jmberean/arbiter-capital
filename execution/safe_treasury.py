import os
import json
import logging
import hashlib
from eth_account import Account
from web3 import Web3
from core.models import Proposal
from core.persistence import STATE_DIR

logger = logging.getLogger("SafeTreasury")

try:
    from safe_eth.eth import EthereumClient
    from safe_eth.safe import Safe
    HAS_SAFE_LIB = True
except ImportError:
    HAS_SAFE_LIB = False
    logger.warning("safe_eth not found. SafeTreasury operating in MOCK mode.")

_NONCE_FILE = STATE_DIR / "mock_safe_nonce.json"


class SafeTreasury:
    def __init__(self):
        self.rpc_url = os.getenv("ETH_RPC_URL", "http://localhost:8545")
        self.safe_address = os.getenv("SAFE_ADDRESS", "")
        self.chain_id = int(os.getenv("CHAIN_ID", "11155111"))
        self.private_key = os.getenv("EXECUTOR_PRIVATE_KEY")

        if not self.safe_address or not self.private_key or not HAS_SAFE_LIB:
            reason = "Library Missing" if not HAS_SAFE_LIB else "Config Missing"
            logger.info("SafeTreasury: MOCK mode (%s)", reason)
            self.mock_mode = True
            self.executor_account = Account.create()
        else:
            self.mock_mode = False
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.client = EthereumClient(self.rpc_url)
            self.safe = Safe(self.safe_address, self.client)
            self.executor_account = Account.from_key(self.private_key)

    def target_address(self) -> str:
        """Returns the Universal Router address — the destination for all Safe txs."""
        addr = os.getenv("UNIVERSAL_ROUTER_ADDRESS", "")
        if not addr:
            logger.warning("UNIVERSAL_ROUTER_ADDRESS not set; using zero address as placeholder")
            return "0x" + "0" * 40
        return addr

    def read_nonce(self) -> int:
        """Returns the current Safe nonce (live: on-chain; mock: persisted in state/)."""
        if not self.mock_mode:
            return self.safe.retrieve_nonce()
        if _NONCE_FILE.exists():
            return json.loads(_NONCE_FILE.read_text()).get("nonce", 0)
        return 0

    def _increment_mock_nonce(self, nonce: int) -> None:
        _NONCE_FILE.write_text(json.dumps({"nonce": nonce + 1}))

    def get_safe_tx_hash(self, to: str, data: bytes, value: int = 0, nonce: int | None = None) -> str:
        """Returns the EIP-712 hash of a Safe transaction."""
        if nonce is None:
            nonce = self.read_nonce()

        if self.mock_mode:
            payload = f"{to}-{data.hex()}-{value}-{nonce}-{self.chain_id}".encode()
            return "0x" + hashlib.sha256(payload).hexdigest()

        safe_tx = self.safe.build_multisig_tx(
            to=to, value=value, data=data, safe_nonce=nonce
        )
        return "0x" + safe_tx.safe_tx_hash.hex()

    def sign_hash(self, safe_tx_hash: str, key: bytes | None = None) -> str:
        """Signs a 32-byte digest (Safe expects raw-hash signatures)."""
        signing_key = key if key is not None else self.executor_account.key
        digest_hex = safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash
        digest = bytes.fromhex(digest_hex)
        if len(digest) != 32:
            raise ValueError(f"safe_tx_hash must be 32 bytes, got {len(digest)}")
        return Account.unsafe_sign_hash(digest, signing_key).signature.hex()

    def execute_with_signatures(self, proposal: Proposal, calldata: bytes, signatures: list) -> str:
        if self.mock_mode:
            nonce = self.read_nonce()
            self._increment_mock_nonce(nonce)
            logger.info("MOCK EXECUTE: proposal=%s sigs=%d nonce=%d",
                        proposal.proposal_id, len(signatures), nonce)
            payload = f"executed-{proposal.proposal_id}-{nonce}".encode()
            return "0x" + hashlib.sha256(payload).hexdigest()

        try:
            nonce = self.read_nonce()
            to = self.target_address()
            safe_tx = self.safe.build_multisig_tx(
                to=to, value=0, data=calldata, safe_nonce=nonce
            )
            # Collect and sort signatures (Safe requires ascending signer address order)
            for sig in signatures:
                safe_tx.signatures = getattr(safe_tx, "signatures", b"") + bytes.fromhex(
                    sig[2:] if sig.startswith("0x") else sig
                )
            tx_hash, _ = safe_tx.execute(self.executor_account.key)
            logger.info("Safe tx submitted: %s (nonce=%d)", tx_hash.hex(), nonce)
            return "0x" + tx_hash.hex()
        except Exception as e:
            logger.error("Safe execution failed: %s", e)
            raise
