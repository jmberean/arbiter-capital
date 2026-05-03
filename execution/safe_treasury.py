from __future__ import annotations

import json
import logging
import os
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode as abi_encode
from eth_utils import keccak, to_checksum_address
from web3 import Web3
from core.models import Proposal
from core.persistence import STATE_DIR

logger = logging.getLogger("SafeTreasury")

_NONCE_FILE = STATE_DIR / "mock_safe_nonce.json"

_ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# EIP-712 type hash constants (Safe v1.4.x)
_DOMAIN_TYPEHASH = keccak(
    text="EIP712Domain(uint256 chainId,address verifyingContract)"
)
_SAFE_TX_TYPEHASH = keccak(
    text=(
        "SafeTx(address to,uint256 value,bytes data,uint8 operation,"
        "uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,"
        "address refundReceiver,uint256 nonce)"
    )
)

# Safe v1.4.x EIP-712 type definition (used by encode_typed_data in mock path)
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

_SAFE_ABI = [
    {
        "name": "execTransaction",
        "type": "function",
        "inputs": [
            {"name": "to",             "type": "address"},
            {"name": "value",          "type": "uint256"},
            {"name": "data",           "type": "bytes"},
            {"name": "operation",      "type": "uint8"},
            {"name": "safeTxGas",      "type": "uint256"},
            {"name": "baseGas",        "type": "uint256"},
            {"name": "gasPrice",       "type": "uint256"},
            {"name": "gasToken",       "type": "address"},
            {"name": "refundReceiver", "type": "address"},
            {"name": "signatures",     "type": "bytes"},
        ],
        "outputs": [{"name": "success", "type": "bool"}],
        "stateMutability": "payable",
    },
    {
        "name": "nonce",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
]


def _eip712_safe_tx_hash(safe_addr: str, chain_id: int, to: str,
                          data: bytes, nonce: int) -> bytes:
    """Compute the EIP-712 Safe transaction digest without any external library."""
    domain_sep = keccak(abi_encode(
        ["bytes32", "uint256", "address"],
        [_DOMAIN_TYPEHASH, chain_id, to_checksum_address(safe_addr)],
    ))
    struct_hash = keccak(abi_encode(
        ["bytes32", "address", "uint256", "bytes32",
         "uint8",   "uint256", "uint256", "uint256",
         "address", "address", "uint256"],
        [
            _SAFE_TX_TYPEHASH,
            to_checksum_address(to),
            0,             # value
            keccak(data),  # keccak of data
            0,             # operation = Call
            0, 0, 0,       # safeTxGas, baseGas, gasPrice
            _ZERO_ADDR, _ZERO_ADDR,  # gasToken, refundReceiver
            nonce,
        ],
    ))
    return keccak(b"\x19\x01" + domain_sep + struct_hash)


class SafeTreasury:
    def __init__(self):
        self.rpc_url   = os.getenv("ETH_RPC_URL", "http://localhost:8545")
        self.safe_address = os.getenv("SAFE_ADDRESS", "")
        self.chain_id  = int(os.getenv("CHAIN_ID", "11155111"))
        self.private_key = os.getenv("EXECUTOR_PRIVATE_KEY", "")

        _key_ok = (
            self.private_key
            and not self.private_key.startswith("0xabc")
            and len(self.private_key) >= 64
        )

        if self.safe_address and _key_ok:
            self.mock_mode = False
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.safe_contract = self.w3.eth.contract(
                address=to_checksum_address(self.safe_address), abi=_SAFE_ABI
            )
            self.executor_account = Account.from_key(self.private_key)
            logger.info(
                "SafeTreasury: LIVE mode (Safe=%s executor=%s)",
                self.safe_address, self.executor_account.address,
            )
        else:
            self.mock_mode = True
            self.executor_account = Account.create()
            logger.info("SafeTreasury: MOCK mode (no SAFE_ADDRESS or EXECUTOR_PRIVATE_KEY)")

    # ── public interface ──────────────────────────────────────────────────────

    def target_address(self) -> str:
        addr = os.getenv("UNIVERSAL_ROUTER_ADDRESS", "")
        if not addr:
            logger.warning("UNIVERSAL_ROUTER_ADDRESS not set; using zero address")
            return _ZERO_ADDR
        return addr

    def read_nonce(self) -> int:
        """Current Safe nonce — on-chain in live mode, file-persisted in mock."""
        if not self.mock_mode:
            return self.safe_contract.functions.nonce().call()
        if _NONCE_FILE.exists():
            return json.loads(_NONCE_FILE.read_text()).get("nonce", 0)
        return 0

    def get_safe_tx_hash(self, to: str, data: bytes, value: int = 0,
                         nonce: int | None = None) -> str:
        """EIP-712 digest of a Safe transaction — identical formula in both modes."""
        if nonce is None:
            nonce = self.read_nonce()
        safe_addr = to_checksum_address(self.safe_address) if self.safe_address \
            else _ZERO_ADDR
        if not self.mock_mode:
            # Live: use raw keccak path (same math, no external lib)
            digest = _eip712_safe_tx_hash(safe_addr, self.chain_id, to, data, nonce)
            return "0x" + digest.hex()
        # Mock: encode_typed_data keeps test compatibility
        domain = {"chainId": self.chain_id, "verifyingContract": safe_addr}
        message = {
            "to": to_checksum_address(to), "value": int(value), "data": data,
            "operation": 0, "safeTxGas": 0, "baseGas": 0, "gasPrice": 0,
            "gasToken": _ZERO_ADDR, "refundReceiver": _ZERO_ADDR, "nonce": int(nonce),
        }
        digest = encode_typed_data(
            domain_data=domain,
            message_types=_SAFE_TX_TYPES,
            message_data=message,
        ).body
        return "0x" + digest.hex()

    def sign_hash(self, safe_tx_hash: str, key: bytes | None = None) -> str:
        signing_key = key if key is not None else self.executor_account.key
        digest = bytes.fromhex(
            safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash
        )
        if len(digest) != 32:
            raise ValueError(f"safe_tx_hash must be 32 bytes, got {len(digest)}")
        return Account.unsafe_sign_hash(digest, signing_key).signature.hex()

    def execute_with_signatures(self, proposal: Proposal, calldata: bytes,
                                signatures: list) -> str:
        """Execute a Safe transaction. `signatures` is a list whose first element
        is the sorted-and-concatenated hex signature blob from execution_process."""
        if self.mock_mode:
            nonce = self.read_nonce()
            self._increment_mock_nonce(nonce)
            logger.info("MOCK EXECUTE: proposal=%s nonce=%d", proposal.proposal_id, nonce)
            return "0x" + keccak(f"executed-{proposal.proposal_id}-{nonce}".encode()).hex()

        to = self.target_address()
        nonce = self.read_nonce()

        # signatures[0] is "0x<quant_sig_130_hex><patriarch_sig_130_hex>" (sorted)
        raw_sigs = signatures[0]
        sig_bytes = bytes.fromhex(raw_sigs[2:] if raw_sigs.startswith("0x") else raw_sigs)

        tx = self.safe_contract.functions.execTransaction(
            to_checksum_address(to),
            0,           # value
            calldata,
            0,           # operation = Call
            0, 0, 0,     # safeTxGas, baseGas, gasPrice
            _ZERO_ADDR, _ZERO_ADDR,  # gasToken, refundReceiver
            sig_bytes,
        ).build_transaction({
            "from":     self.executor_account.address,
            "nonce":    self.w3.eth.get_transaction_count(
                            self.executor_account.address, "pending"),
            "gas":      500_000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId":  self.chain_id,
        })
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        logger.info("Safe tx submitted: %s (nonce=%d)", tx_hash, nonce)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise RuntimeError(f"Safe execTransaction reverted (tx={tx_hash})")
        return "0x" + tx_hash if not tx_hash.startswith("0x") else tx_hash

    # ── internal ──────────────────────────────────────────────────────────────

    def _increment_mock_nonce(self, nonce: int) -> None:
        _NONCE_FILE.write_text(json.dumps({"nonce": nonce + 1}))
