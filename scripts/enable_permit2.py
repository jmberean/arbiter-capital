"""
One-time Permit2 approvals: grant the Universal Router permission to spend
WETH, USDC, stETH, and WBTC from the Arbiter Safe.

Calls Permit2.approve(token, universalRouter, maxAmount, maxExpiry) once per
asset as a Safe multisig transaction signed by QUANT_KEY + PATRIARCH_KEY.

Run after:
  - Step 3 (Safe deployed)
  - Step 7 (KeeperHub MCP server running is NOT required — this script
             calls the Safe contract directly via web3)

Usage:
    python scripts/enable_permit2.py

Required .env:
    SAFE_ADDRESS, ETH_RPC_URL
    QUANT_PRIVATE_KEY, PATRIARCH_PRIVATE_KEY
    EXECUTOR_PRIVATE_KEY          # pays gas for execTransaction
    PERMIT2_ADDRESS
    UNIVERSAL_ROUTER_ADDRESS
    WETH_ADDRESS, USDC_ADDRESS, STETH_ADDRESS, WBTC_ADDRESS
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_account import Account
from eth_abi import encode

# ── env ──────────────────────────────────────────────────────────────────────

RPC_URL          = os.environ["ETH_RPC_URL"]
SAFE_ADDR        = Web3.to_checksum_address(os.environ["SAFE_ADDRESS"])
PERMIT2_ADDR     = Web3.to_checksum_address(os.environ["PERMIT2_ADDRESS"])
ROUTER_ADDR      = Web3.to_checksum_address(os.environ["UNIVERSAL_ROUTER_ADDRESS"])
QUANT_KEY        = os.environ["QUANT_PRIVATE_KEY"]
PATRIARCH_KEY    = os.environ["PATRIARCH_PRIVATE_KEY"]
EXECUTOR_KEY     = os.environ["EXECUTOR_PRIVATE_KEY"]
CHAIN_ID         = int(os.getenv("CHAIN_ID", "11155111"))  # Sepolia

TOKENS = {
    "WETH":  Web3.to_checksum_address(os.environ["WETH_ADDRESS"]),
    "USDC":  Web3.to_checksum_address(os.environ["USDC_ADDRESS"]),
    "stETH": Web3.to_checksum_address(os.environ["STETH_ADDRESS"]),
    "WBTC":  Web3.to_checksum_address(os.environ["WBTC_ADDRESS"]),
}

QUANT_ADDR     = Account.from_key(QUANT_KEY).address
PATRIARCH_ADDR = Account.from_key(PATRIARCH_KEY).address
EXECUTOR_ADDR  = Account.from_key(EXECUTOR_KEY).address

MAX_UINT160 = 2**160 - 1
MAX_UINT48  = 2**48 - 1

# ── EIP-712 Safe transaction hash ────────────────────────────────────────────

from eth_utils import keccak

DOMAIN_TYPEHASH = keccak(
    text="EIP712Domain(uint256 chainId,address verifyingContract)"
)
SAFE_TX_TYPEHASH = keccak(
    text=(
        "SafeTx(address to,uint256 value,bytes data,uint8 operation,"
        "uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,"
        "address refundReceiver,uint256 nonce)"
    )
)


def _compute_safe_tx_hash(to: str, data: bytes, nonce: int) -> bytes:
    """EIP-712 Safe transaction digest — matches Gnosis Safe v1.4.x on-chain."""
    domain_separator = keccak(encode(
        ["bytes32", "uint256", "address"],
        [DOMAIN_TYPEHASH, CHAIN_ID, SAFE_ADDR],
    ))
    struct_hash = keccak(encode(
        ["bytes32", "address", "uint256", "bytes32",
         "uint8",   "uint256", "uint256", "uint256",
         "address", "address", "uint256"],
        [
            SAFE_TX_TYPEHASH,
            Web3.to_checksum_address(to),
            0,                          # value
            keccak(data),               # data hash
            0,                          # operation = Call
            0,                          # safeTxGas
            0,                          # baseGas
            0,                          # gasPrice
            "0x0000000000000000000000000000000000000000",  # gasToken
            "0x0000000000000000000000000000000000000000",  # refundReceiver
            nonce,
        ],
    ))
    return keccak(b"\x19\x01" + domain_separator + struct_hash)


# ── Permit2.approve calldata ──────────────────────────────────────────────────

APPROVE_SELECTOR = keccak(text="approve(address,address,uint160,uint48)")[:4]


def _permit2_approve_calldata(token: str) -> bytes:
    packed = encode(
        ["address", "address", "uint160", "uint48"],
        [
            Web3.to_checksum_address(token),
            ROUTER_ADDR,
            MAX_UINT160,
            MAX_UINT48,
        ],
    )
    return APPROVE_SELECTOR + packed


# ── Safe.execTransaction ──────────────────────────────────────────────────────

SAFE_ABI = [
    {
        "name": "execTransaction",
        "type": "function",
        "inputs": [
            {"name": "to",              "type": "address"},
            {"name": "value",           "type": "uint256"},
            {"name": "data",            "type": "bytes"},
            {"name": "operation",       "type": "uint8"},
            {"name": "safeTxGas",       "type": "uint256"},
            {"name": "baseGas",         "type": "uint256"},
            {"name": "gasPrice",        "type": "uint256"},
            {"name": "gasToken",        "type": "address"},
            {"name": "refundReceiver",  "type": "address"},
            {"name": "signatures",      "type": "bytes"},
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


def _pack_signatures(digest: bytes) -> bytes:
    """Sign with both owners, sort by address ascending (Safe requirement)."""
    sig_q = Account.unsafe_sign_hash(digest, QUANT_KEY).signature
    sig_p = Account.unsafe_sign_hash(digest, PATRIARCH_KEY).signature
    pairs = sorted(
        [(QUANT_ADDR, sig_q), (PATRIARCH_ADDR, sig_p)],
        key=lambda x: int(x[0], 16),
    )
    return b"".join(sig for _, sig in pairs)


def _execute_safe_tx(w3: Web3, safe_contract, to: str, calldata: bytes, nonce: int) -> str:
    digest = _compute_safe_tx_hash(to, calldata, nonce)
    sigs   = _pack_signatures(digest)

    zero  = "0x0000000000000000000000000000000000000000"
    tx    = safe_contract.functions.execTransaction(
        to, 0, calldata, 0, 0, 0, 0, zero, zero, sigs,
    ).build_transaction({
        "from":  EXECUTOR_ADDR,
        "nonce": w3.eth.get_transaction_count(EXECUTOR_ADDR),
        "gas":   300_000,
    })
    signed = Account.sign_transaction(tx, EXECUTOR_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {RPC_URL}")
        sys.exit(1)

    balance = w3.eth.get_balance(EXECUTOR_ADDR)
    if balance < w3.to_wei(0.01, "ether"):
        print(f"ERROR: Executor {EXECUTOR_ADDR} has only {w3.from_wei(balance,'ether'):.4f} ETH — need ≥0.01 ETH")
        sys.exit(1)

    safe = w3.eth.contract(address=SAFE_ADDR, abi=SAFE_ABI)

    print(f"Safe:              {SAFE_ADDR}")
    print(f"Permit2:           {PERMIT2_ADDR}")
    print(f"Universal Router:  {ROUTER_ADDR}")
    print(f"Executor:          {EXECUTOR_ADDR} ({w3.from_wei(balance,'ether'):.4f} ETH)")
    print()

    for symbol, token_addr in TOKENS.items():
        nonce    = safe.functions.nonce().call()
        calldata = _permit2_approve_calldata(token_addr)

        print(f"Approving {symbol} ({token_addr})  nonce={nonce} ...")
        try:
            tx_hash = _execute_safe_tx(w3, safe, PERMIT2_ADDR, calldata, nonce)
            print(f"  submitted: 0x{tx_hash}")
            # wait for inclusion before incrementing nonce
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            status  = "OK" if receipt.status == 1 else "FAILED"
            print(f"  mined:     block={receipt.blockNumber}  status={status}")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            print("  Skipping remaining tokens — fix and re-run.")
            sys.exit(1)

    print("\nAll Permit2 approvals complete.")
    print("Run the E2E test (Step 9) next.")


if __name__ == "__main__":
    main()
