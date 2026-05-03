import os
from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account

load_dotenv(override=True)

rpc_url = os.getenv("ETH_RPC_URL")
safe_addr = os.getenv("SAFE_ADDRESS")
executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")

if not rpc_url or not safe_addr or not executor_key:
    print("Missing env vars (ETH_RPC_URL, SAFE_ADDRESS, EXECUTOR_PRIVATE_KEY)")
    exit(1)

w3 = Web3(Web3.HTTPProvider(rpc_url))
if not w3.is_connected():
    print("Web3 not connected")
    exit(1)

executor_addr = Account.from_key(executor_key).address

print(f"--- Balances (Sepolia) ---")
safe_balance = w3.eth.get_balance(safe_addr)
print(f"Safe ({safe_addr}): {w3.from_wei(safe_balance, 'ether')} ETH")

exec_balance = w3.eth.get_balance(executor_addr)
print(f"Executor ({executor_addr}): {w3.from_wei(exec_balance, 'ether')} ETH")

# Check for USDC balance in Safe
USDC_ADDR = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
# ERC20 minimal ABI
abi = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
usdc_contract = w3.eth.contract(address=w3.to_checksum_address(USDC_ADDR), abi=abi)
try:
    usdc_bal = usdc_contract.functions.balanceOf(safe_addr).call()
    print(f"Safe USDC: {usdc_bal / 1e6} USDC")
except Exception as e:
    print(f"Failed to fetch USDC balance: {e}")

# Check the reverted TX
tx_hash = "0xde5526f19cb3363cd152be52c4134f3d959eb68bb37ad18fd2352c395ea2ff11"
print(f"\n--- Investigating TX {tx_hash} ---")
try:
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    if receipt['status'] == 0:
        print("Status: REVERTED")
        # Try to get revert reason by re-playing call
        tx = w3.eth.get_transaction(tx_hash)
        try:
            # We can't easily replay a Safe execTransaction without the exactly state, 
            # but we can check if it failed due to gas or Safe's internal logic.
            print(f"Gas Used: {receipt['gasUsed']} / {tx['gas']}")
            if receipt['gasUsed'] == tx['gas']:
                print("Likely out of gas.")
        except:
            pass
    else:
        print("Status: SUCCESS (Wait, the log said it reverted?)")
except Exception as e:
    print(f"Could not find receipt or error: {e}")
