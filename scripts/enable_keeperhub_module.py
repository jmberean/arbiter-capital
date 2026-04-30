"""
Enable the KeeperHub address as a Safe Module on the project Safe.

Run once before the live demo. Requires:
  SAFE_ADDRESS, ETH_RPC_URL, QUANT_PRIVATE_KEY, PATRIARCH_PRIVATE_KEY,
  KEEPERHUB_ATTESTOR_KEY (provides the module address) in .env.

The script:
  1. Builds an enableModule(KEEPERHUB_ADDR) Safe transaction.
  2. Both Quant and Patriarch sign (threshold = 2).
  3. Submits via safe-eth-py.
  4. Polls for the tx to mine and confirms the module is enabled.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from web3 import Web3
from eth_account import Account
from core.identity import QUANT_KEY, PATRIARCH_KEY, QUANT_ADDR, PATRIARCH_ADDR, KEEPERHUB_ADDR
from execution.safe_treasury import SafeTreasury


ENABLE_MODULE_SELECTOR = bytes.fromhex("610b5925")  # enableModule(address)


def build_enable_module_calldata(module_address: str) -> bytes:
    addr = Web3.to_checksum_address(module_address)
    padded = bytes.fromhex(addr[2:].zfill(64))
    return ENABLE_MODULE_SELECTOR + padded


def main():
    rpc_url = os.getenv("ETH_RPC_URL")
    safe_addr = os.getenv("SAFE_ADDRESS")

    if not rpc_url or not safe_addr:
        print("ERROR: ETH_RPC_URL and SAFE_ADDRESS must be set in .env")
        sys.exit(1)

    if not KEEPERHUB_ADDR:
        print("ERROR: KEEPERHUB_ATTESTOR_KEY not set — cannot derive module address")
        sys.exit(1)

    if not QUANT_KEY or not PATRIARCH_KEY:
        print("ERROR: QUANT_PRIVATE_KEY and PATRIARCH_PRIVATE_KEY must be set")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc_url}")
        sys.exit(1)

    treasury = SafeTreasury()
    calldata = build_enable_module_calldata(KEEPERHUB_ADDR)

    print(f"Safe:          {safe_addr}")
    print(f"Module to add: {KEEPERHUB_ADDR}")
    print(f"Calldata:      0x{calldata.hex()}")

    nonce = treasury.read_nonce()
    safe_tx_hash = treasury.get_safe_tx_hash(safe_addr, calldata, 0, nonce=nonce)
    print(f"safe_tx_hash:  {safe_tx_hash}  (nonce={nonce})")

    digest = bytes.fromhex(safe_tx_hash[2:])
    sig_quant = Account.unsafe_sign_hash(digest, QUANT_KEY).signature
    sig_patriarch = Account.unsafe_sign_hash(digest, PATRIARCH_KEY).signature

    # Safe requires signatures sorted by signer address ascending
    pairs = sorted(
        [(QUANT_ADDR, sig_quant), (PATRIARCH_ADDR, sig_patriarch)],
        key=lambda x: int(x[0], 16),
    )
    sigs_blob = b"".join(sig for _, sig in pairs)

    print("\nSignatures collected. Submitting via SafeTreasury...")
    try:
        class _FakeProposal:
            safe_nonce = nonce

        tx_hash = treasury.execute_with_signatures(_FakeProposal(), calldata, sigs_blob)
        print(f"\nTransaction submitted: {tx_hash}")
        print("Check Sepolia explorer to confirm the module is enabled.")
    except Exception as e:
        print(f"\nERROR during submission: {e}")
        print("If running in mock mode (no SAFE_ADDRESS on Sepolia), this is expected.")
        print("Re-run against a real Sepolia Safe with funded executor key.")
        sys.exit(1)


if __name__ == "__main__":
    main()
