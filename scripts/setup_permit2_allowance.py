"""
One-time setup: approve WETH → Permit2 from the Safe.

Permit2 allowance (Safe→UniversalRouter) is already MAX from a previous tx.
This script only needs to submit the WETH.approve(Permit2, MAX) transaction
so Permit2 can actually pull WETH from the Safe.

Run once:
    PYTHONPATH=. python scripts/setup_permit2_allowance.py
"""
from __future__ import annotations

import os
import sys
import time
import logging
from dotenv import load_dotenv
load_dotenv(override=True)

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_abi import encode
from eth_utils import keccak, to_checksum_address

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("Permit2Setup")

WETH    = to_checksum_address("0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14")
PERMIT2 = to_checksum_address("0x000000000022D473030F116dDEE9F6B43aC78BA3")
MAX_UINT256 = 2**256 - 1

_SAFE_ABI = [
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},
               {"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},
               {"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},
               {"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},
               {"name":"refundReceiver","type":"address"},
               {"name":"signatures","type":"bytes"}],
     "name":"execTransaction","outputs":[{"type":"bool"}],"stateMutability":"payable","type":"function"},
    {"inputs":[],"name":"nonce","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},
               {"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},
               {"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},
               {"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},
               {"name":"refundReceiver","type":"address"},{"name":"_nonce","type":"uint256"}],
     "name":"getTransactionHash","outputs":[{"type":"bytes32"}],"stateMutability":"view","type":"function"},
]

_ERC20_APPROVE_SIG = keccak(text="approve(address,uint256)")[:4]


def build_approve_calldata(spender: str, amount: int) -> bytes:
    return _ERC20_APPROVE_SIG + encode(["address", "uint256"], [spender, amount])


def main():
    rpc      = os.getenv("ETH_RPC_URL") or os.getenv("SEPOLIA_RPC")
    safe_addr = to_checksum_address(os.getenv("SAFE_ADDRESS", ""))
    quant_key  = os.getenv("QUANT_PRIVATE_KEY", "")
    patri_key  = os.getenv("PATRIARCH_PRIVATE_KEY", "")
    exec_key   = os.getenv("EXECUTOR_PRIVATE_KEY", "")

    if not all([rpc, safe_addr, quant_key, patri_key, exec_key]):
        logger.error("Missing env vars: ETH_RPC_URL, SAFE_ADDRESS, QUANT_PRIVATE_KEY, PATRIARCH_PRIVATE_KEY, EXECUTOR_PRIVATE_KEY")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    assert w3.is_connected(), "Cannot connect to RPC"

    quant  = Account.from_key(quant_key)
    patri  = Account.from_key(patri_key)
    executor = Account.from_key(exec_key)

    safe = w3.eth.contract(address=safe_addr, abi=_SAFE_ABI)

    # Check current allowance
    approve_sel = keccak(text="allowance(address,address)")[:4]
    data = approve_sel + b"\x00"*12 + bytes.fromhex(safe_addr[2:]) + b"\x00"*12 + bytes.fromhex(PERMIT2[2:])
    current = int.from_bytes(w3.eth.call({"to": WETH, "data": data.hex()}), "big")
    if current > 0:
        logger.info("WETH allowance to Permit2 already set (%d). Nothing to do.", current)
        return

    # Build the inner calldata: WETH.approve(Permit2, MAX_UINT256)
    inner_data = build_approve_calldata(PERMIT2, MAX_UINT256)

    nonce = safe.functions.nonce().call()
    safe_tx_hash = safe.functions.getTransactionHash(
        WETH, 0, inner_data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        nonce,
    ).call()

    # Sign with both Safe owners
    def sign(key_account) -> str:
        sig = Account.unsafe_sign_hash(safe_tx_hash, private_key=key_account.key)
        v = sig.v
        r = sig.r.to_bytes(32, "big")
        s = sig.s.to_bytes(32, "big")
        return (r + s + bytes([v])).hex()

    sigs = {quant.address: sign(quant), patri.address: sign(patri)}
    # Safe requires signatures sorted by signer address
    sorted_sigs = "".join(v for _, v in sorted(sigs.items(), key=lambda x: x[0].lower()))
    signatures = bytes.fromhex(sorted_sigs)

    logger.info("Submitting WETH.approve(Permit2, MAX) from Safe...")
    tx = safe.functions.execTransaction(
        WETH, 0, inner_data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        signatures,
    ).build_transaction({
        "from": executor.address,
        "nonce": w3.eth.get_transaction_count(executor.address),
        "gas": 150000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, exec_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    logger.info("Tx submitted: 0x%s", tx_hash)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status == 1:
        logger.info("✓ WETH→Permit2 approval set. Safe is ready for swaps.")
    else:
        logger.error("✗ Transaction reverted. Check Etherscan: https://sepolia.etherscan.io/tx/0x%s", tx_hash)


if __name__ == "__main__":
    main()
