import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(override=True)

rpc_url = os.getenv("ETH_RPC_URL")
safe_addr = os.getenv("SAFE_ADDRESS")

w3 = Web3(Web3.HTTPProvider(rpc_url))
safe_abi = [{"constant": True, "inputs": [], "name": "nonce", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
safe = w3.eth.contract(address=Web3.to_checksum_address(safe_addr), abi=safe_abi)

print(f"Current On-Chain Nonce: {safe.functions.nonce().call()}")
