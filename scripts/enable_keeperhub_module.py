"""
Enable the KeeperHub address as a Safe Module on the project Safe.

Run once before the live demo. Requires:
  SAFE_ADDRESS, SEPOLIA_RPC (or ETH_RPC_URL), QUANT_PRIVATE_KEY,
  PATRIARCH_PRIVATE_KEY, EXECUTOR_PRIVATE_KEY, KEEPERHUB_ATTESTOR_KEY in .env.

Uses web3 directly (no safe_eth dependency) to call execTransaction.
Hash is fetched from the Safe's own getTransactionHash view — no local EIP-712
re-implementation needed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(override=True)

from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address
from core.identity import (
    QUANT_KEY, PATRIARCH_KEY, QUANT_ADDR, PATRIARCH_ADDR,
    EXECUTOR_KEY, KEEPERHUB_ADDR,
)

ZERO_ADDR = "0x" + "0" * 40

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
    {
        "name": "isModuleEnabled",
        "type": "function",
        "inputs": [{"name": "module", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
    {
        "name": "getTransactionHash",
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
            {"name": "_nonce",         "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
    },
]

ENABLE_MODULE_SELECTOR = bytes.fromhex("610b5925")  # enableModule(address)


def build_calldata(module_address: str) -> bytes:
    addr = to_checksum_address(module_address)
    padded = bytes.fromhex(addr[2:].zfill(64))
    return ENABLE_MODULE_SELECTOR + padded


def main():
    rpc_url = os.getenv("SEPOLIA_RPC") or os.getenv("ETH_RPC_URL")
    safe_addr = os.getenv("SAFE_ADDRESS")
    chain_id = int(os.getenv("CHAIN_ID", "11155111"))

    for label, val in [("SEPOLIA_RPC/ETH_RPC_URL", rpc_url), ("SAFE_ADDRESS", safe_addr)]:
        if not val:
            print(f"ERROR: {label} must be set in .env")
            sys.exit(1)

    if not KEEPERHUB_ADDR:
        print("ERROR: KEEPERHUB_ATTESTOR_KEY not set — cannot derive module address")
        sys.exit(1)
    if not QUANT_KEY or not PATRIARCH_KEY:
        print("ERROR: QUANT_PRIVATE_KEY and PATRIARCH_PRIVATE_KEY must be set")
        sys.exit(1)
    if not EXECUTOR_KEY:
        print("ERROR: EXECUTOR_PRIVATE_KEY must be set (gas payer)")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc_url}")
        sys.exit(1)

    safe_contract = w3.eth.contract(
        address=to_checksum_address(safe_addr),
        abi=SAFE_ABI,
    )

    if safe_contract.functions.isModuleEnabled(
        to_checksum_address(KEEPERHUB_ADDR)
    ).call():
        print(f"Module {KEEPERHUB_ADDR} is already enabled — nothing to do.")
        return

    nonce = safe_contract.functions.nonce().call()
    calldata = build_calldata(KEEPERHUB_ADDR)

    print(f"Safe:          {safe_addr}")
    print(f"Module to add: {KEEPERHUB_ADDR}")
    print(f"Safe nonce:    {nonce}")
    print(f"Chain ID:      {chain_id}")

    # Fetch exact hash from the contract — avoids any local EIP-712 domain mismatch
    digest = safe_contract.functions.getTransactionHash(
        to_checksum_address(safe_addr),  # enableModule is a Safe self-call
        0, calldata, 0, 0, 0, 0, ZERO_ADDR, ZERO_ADDR, nonce,
    ).call()
    print(f"safe_tx_hash:  0x{digest.hex()}")

    sig_quant     = Account.unsafe_sign_hash(digest, QUANT_KEY).signature
    sig_patriarch = Account.unsafe_sign_hash(digest, PATRIARCH_KEY).signature

    # Safe requires signatures sorted by signer address (ascending)
    pairs = sorted(
        [(QUANT_ADDR, sig_quant), (PATRIARCH_ADDR, sig_patriarch)],
        key=lambda x: int(x[0], 16),
    )
    sigs_blob = b"".join(sig for _, sig in pairs)
    print(f"Signers:       {[addr for addr, _ in pairs]}")

    executor = Account.from_key(EXECUTOR_KEY)
    print(f"Executor:      {executor.address}")

    tx = safe_contract.functions.execTransaction(
        to_checksum_address(safe_addr),
        0,
        calldata,
        0,
        0, 0, 0,
        ZERO_ADDR,
        ZERO_ADDR,
        sigs_blob,
    ).build_transaction({
        "from":                 executor.address,
        "nonce":                w3.eth.get_transaction_count(executor.address),
        "gas":                  300_000,
        "maxFeePerGas":         w3.to_wei(30, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
        "chainId":              chain_id,
    })

    signed = executor.sign_transaction(tx)
    print("\nBroadcasting transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Submitted: 0x{tx_hash.hex()}")
    print("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    url = f"https://sepolia.etherscan.io/tx/0x{tx_hash.hex()}"
    if receipt["status"] == 1:
        print(f"\nSUCCESS — KeeperHub module enabled in block {receipt['blockNumber']}")
        print(f"Tx: {url}")
    else:
        print(f"\nREVERTED — {url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
