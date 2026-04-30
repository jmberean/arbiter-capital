from __future__ import annotations

import json
import logging
import os
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address
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

# Safe v1.4.x EIP-712 SafeTx type used in mock mode so the digest still
# round-trips through encode_typed_data.
_SAFE_TX_TYPES = {
    "SafeTx": [
        {"name": "to",             "type": "address"},
        {"name": "value",          "type": "uint256"},
        {"name": "data",           "type": "bytes"},
        {"name": "operation",      "type": "uint8"},
        {"name": "safeTxGas",      "type": "uint256"},
        {"name": "baseGas",        "type": "uint256"},
        {"name": "gasPrice",       "type": "uint256"},
        {"name": "gasToken",       "type": "address"},
        {"name": "refundReceiver", "type": "address"},
        {"name": "nonce",          "type": "uint256"},
    ]
}


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

    def get_safe_tx_hash(self, to: str, data: bytes, value: int = 0,
                         nonce: int | None = None) -> str:
        """Returns the EIP-712 hash of a Safe transaction.

        In live mode, defers to safe_eth.Safe.build_multisig_tx.safe_tx_hash.
        In mock mode, computes the same EIP-712 SafeTx digest using
        encode_typed_data so that signatures produced over the digest are
        wire-compatible with what the live Safe contract would accept.
        """
        if nonce is None:
            nonce = self.read_nonce()

        if self.mock_mode:
            safe_addr = to_checksum_address(self.safe_address) if self.safe_address \
                else "0x" + "0" * 40
            domain = {
                "chainId": self.chain_id,
                "verifyingContract": safe_addr,
            }
            message = {
                "to":             to_checksum_address(to),
                "value":          int(value),
                "data":           data,
                "operation":      0,
                "safeTxGas":      0,
                "baseGas":        0,
                "gasPrice":       0,
                "gasToken":       "0x" + "0" * 40,
                "refundReceiver": "0x" + "0" * 40,
                "nonce":          int(nonce),
            }
            digest = encode_typed_data(domain, _SAFE_TX_TYPES, "SafeTx", message).body
            return "0x" + digest.hex()

        safe_tx = self.safe.build_multisig_tx(
            to=to, value=value, data=data, safe_nonce=nonce
        )
        return "0x" + safe_tx.safe_tx_hash.hex()

    def sign_hash(self, safe_tx_hash: str, key: bytes | None = None) -> str:
        signing_key = key if key is not None else self.executor_account.key
        digest_hex = safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash
        digest = bytes.fromhex(digest_hex)
        if len(digest) != 32:
            raise ValueError(f"safe_tx_hash must be 32 bytes, got {len(digest)}")
        return Account.unsafe_sign_hash(digest, signing_key).signature.hex()

    def execute_with_signatures(self, proposal: Proposal, calldata: bytes,
                                signatures: list) -> str:
        if self.mock_mode:
            nonce = self.read_nonce()
            self._increment_mock_nonce(nonce)
            logger.info(
                "MOCK EXECUTE: proposal=%s sigs=%d nonce=%d",
                proposal.proposal_id, len(signatures), nonce,
            )
            payload = f"executed-{proposal.proposal_id}-{nonce}".encode()
            return "0x" + keccak(payload).hex()

        try:
            nonce = self.read_nonce()
            to = self.target_address()
            safe_tx = self.safe.build_multisig_tx(
                to=to, value=0, data=calldata, safe_nonce=nonce
            )
            for sig in signatures:
                raw = sig[2:] if sig.startswith("0x") else sig
                safe_tx.signatures = getattr(safe_tx, "signatures", b"") + bytes.fromhex(raw)
            tx_hash, _ = safe_tx.execute(self.executor_account.key)
            logger.info("Safe tx submitted: %s (nonce=%d)", tx_hash.hex(), nonce)
            return "0x" + tx_hash.hex()
        except Exception as e:
            logger.error("Safe execution failed: %s", e)
            raise
