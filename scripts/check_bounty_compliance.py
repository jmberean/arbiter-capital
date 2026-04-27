import os, sys, glob

def check_compliance():
    print("🔍 Running Bounty Compliance Gate v5.0...")
    errors = []
    
    # 1. Gensyn AXL Compliance (No centralized brokers)
    # Check if network.py has fallback to centralized logic that isn't guarded
    with open("core/network.py", "r") as f:
        content = f.read()
        if "DEMO_MODE" not in content or "_assert_demo_transport" not in content:
            errors.append("Gensyn: network.py missing DEMO_MODE/AXL enforcement.")

    # 2. 0G Compliance (Permanent Audit Trail)
    # Check if MemoryManager actually writes to 0G RPC
    with open("memory/memory_manager.py", "r") as f:
        content = f.read()
        if "send_raw_transaction" not in content:
            errors.append("0G: MemoryManager does not appear to use Web3 for 0G L1 persistence.")

    # 3. Uniswap v4 Compliance
    # Check for hook files
    v4_files = glob.glob("execution/uniswap_v4/*.py")
    if not any("hook" in f.lower() for f in v4_files) and not os.path.exists("contracts/ArbiterThrottleHook.sol"):
        errors.append("Uniswap: No v4 Hook implementation found.")

    # 4. KeeperHub Compliance (MCP usage)
    with open("execution/keeper_hub.py", "r") as f:
        content = f.read()
        if "ClientSession" not in content or "call_tool" not in content:
            errors.append("KeeperHub: keeper_hub.py does not use MCP ClientSession.")

    # 5. EIP-712 Compliance
    if not os.path.exists("core/crypto.py"):
        errors.append("General: core/crypto.py (EIP-712) missing.")

    if errors:
        print("\n❌ COMPLIANCE FAILED:")
        for e in errors: print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n✅ ALL BOUNTY REQUIREMENTS MET.")

if __name__ == "__main__":
    check_compliance()
