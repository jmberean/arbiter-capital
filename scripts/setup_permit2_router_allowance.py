import os
import sys
import time
import logging
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_abi import encode
from eth_utils import keccak, to_checksum_address

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("Permit2RouterSetup")

WETH = to_checksum_address("0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14")
PERMIT2 = to_checksum_address("0x000000000022D473030F116dDEE9F6B43aC78BA3")
UNIVERSAL_ROUTER = to_checksum_address(os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x3A9D48AB9751398BbFa63ad67599Bb04e4BdF98b"))

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

def main():
    rpc = os.getenv("ETH_RPC_URL")
    safe_addr = to_checksum_address(os.getenv("SAFE_ADDRESS", ""))
    quant_key = os.getenv("QUANT_PRIVATE_KEY", "")
    patri_key = os.getenv("PATRIARCH_PRIVATE_KEY", "")
    exec_key = os.getenv("EXECUTOR_PRIVATE_KEY", "")

    w3 = Web3(Web3.HTTPProvider(rpc))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    quant = Account.from_key(quant_key)
    patri = Account.from_key(patri_key)
    executor = Account.from_key(exec_key)

    safe = w3.eth.contract(address=safe_addr, abi=_SAFE_ABI)

    # Permit2.approve(address token, address spender, uint160 amount, uint48 expiration)
    amount = 2**160 - 1
    expiration = int(time.time()) + 10 * 365 * 24 * 60 * 60 # 10 years
    approve_sel = keccak(text="approve(address,address,uint160,uint48)")[:4]
    inner_data = approve_sel + encode(["address", "address", "uint160", "uint48"], [WETH, UNIVERSAL_ROUTER, amount, expiration])

    nonce = safe.functions.nonce().call()
    safe_tx_hash = safe.functions.getTransactionHash(
        PERMIT2, 0, inner_data, 0, 0, 0, 0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        nonce,
    ).call()

    def sign(key_account) -> str:
        sig = Account.unsafe_sign_hash(safe_tx_hash, private_key=key_account.key)
        v = sig.v
        r = sig.r.to_bytes(32, "big")
        s = sig.s.to_bytes(32, "big")
        return (r + s + bytes([v])).hex()

    sigs = {quant.address: sign(quant), patri.address: sign(patri)}
    sorted_sigs = "".join(v for _, v in sorted(sigs.items(), key=lambda x: x[0].lower()))
    signatures = bytes.fromhex(sorted_sigs)

    logger.info("Submitting Permit2.approve(UniversalRouter) from Safe...")
    tx = safe.functions.execTransaction(
        PERMIT2, 0, inner_data, 0, 0, 0, 0,
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
        logger.info("✓ Permit2→UniversalRouter approval set.")
    else:
        logger.error("✗ Transaction reverted.")

if __name__ == "__main__":
    main()
