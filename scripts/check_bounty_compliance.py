"""Bounty compliance gate. Exit 0 = ship-ready. Non-zero = fix before submitting."""
import glob
import os
import sys

# Ensure project root is on path when run from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def check_compliance():
    print("Running Bounty Compliance Gate v5.0...")
    errors = []
    ok = []

    def check(name, condition, detail=""):
        if condition:
            ok.append(f"  PASS  {name} {detail}")
        else:
            errors.append(f"  FAIL  {name} {detail}")

    # 1. Gensyn AXL — no centralized broker on demo path
    with open("core/network.py", encoding="utf-8") as f:
        net = f.read()
    check("gensyn.demo_mode_guard",
          "DEMO_MODE" in net and "_assert_demo_transport" in net,
          "(network.py fail-closed enforcement)")

    # 2. 0G — MemoryManager writes to chain + hash-chaining
    with open("memory/memory_manager.py", encoding="utf-8") as f:
        mm = f.read()
    check("zerog.live_writes", "send_raw_transaction" in mm, "(Web3 0G persistence)")
    check("zerog.hash_chain", "prev_0g_tx_hash" in mm and "receipt_hash" in mm,
          "(hash-chained receipts)")
    check("zerog.audit_chain_module", os.path.exists("memory/audit_chain.py"),
          "(audit_chain.py)")

    # 3. 0G — replay tool
    check("zerog.replay_script", os.path.exists("scripts/replay_decision.py"),
          "(replay_decision.py)")

    # 4. Uniswap v4 — hook implementation
    has_throttle_hook = os.path.exists("contracts/ArbiterThrottleHook.sol")
    check("uniswap.throttle_hook", has_throttle_hook, "(ArbiterThrottleHook.sol)")

    # 5. Uniswap v4 — SBT receipt contract
    check("uniswap.arbiter_receipt_sbt", os.path.exists("contracts/ArbiterReceipt.sol"),
          "(ArbiterReceipt.sol)")

    # 6. KeeperHub F1 — MCP client
    with open("execution/keeper_hub.py", encoding="utf-8") as f:
        kh = f.read()
    check("keeperhub.f1_mcp_client", "ClientSession" in kh and "call_tool" in kh,
          "(MCP ClientSession)")

    # 7. KeeperHub F2 — LangChain bridge
    check("keeperhub.f2_langchain_bridge", os.path.exists("langchain_keeperhub.py"),
          "(langchain_keeperhub.py)")
    try:
        from langchain_keeperhub import KeeperHubSimulateTool, KeeperHubExecuteTool
        from langchain_core.tools import BaseTool
        check("keeperhub.f2_importable",
              isinstance(KeeperHubSimulateTool(), BaseTool) and isinstance(KeeperHubExecuteTool(), BaseTool),
              "(BaseTool subclass)")
    except Exception as e:
        check("keeperhub.f2_importable", False, f"(import error: {e})")

    # 8. KeeperHub builder feedback
    fb_path = "docs/KEEPERHUB_FEEDBACK.md"
    if os.path.exists(fb_path):
        with open(fb_path, encoding="utf-8") as f:
            fb_text = f.read()
        check("keeperhub.builder_feedback",
              os.path.getsize(fb_path) >= 4096 and fb_text.count("\n## ") >= 3,
              f"(size={os.path.getsize(fb_path)}, h2_sections={fb_text.count(chr(10)+'## ')})")
    else:
        check("keeperhub.builder_feedback", False, "(docs/KEEPERHUB_FEEDBACK.md missing)")

    # 9. EIP-712
    check("crypto.eip712", os.path.exists("core/crypto.py"), "(core/crypto.py)")

    # 10. Byzantine Watchdog — all 6 attacks
    with open("byzantine_watchdog.py", encoding="utf-8") as f:
        wd = f.read()
    check("watchdog.all_attacks",
          all(f"attack_A{i}" in wd for i in range(1, 7)),
          "(A1-A6 all present)")

    # 11. verify_audit --walk-from-head
    with open("verify_audit.py", encoding="utf-8") as f:
        va = f.read()
    check("audit.walk_from_head", "walk_from_head" in va and "walk_chain" in va,
          "(verify_audit.py chain walk)")

    # 12. Public verifier page + server (elite-5b)
    check("verifier.html", os.path.exists("monitor/public_verifier/index.html"),
          "(monitor/public_verifier/index.html)")
    check("verifier.server", os.path.exists("monitor/public_verifier/server.py"),
          "(monitor/public_verifier/server.py)")

    # Print results
    print()
    for line in ok:
        print(line)
    for line in errors:
        print(line)
    print(f"\n{len(ok)}/{len(ok) + len(errors)} checks passed.")

    if errors:
        sys.exit(1)
    else:
        print("ALL BOUNTY REQUIREMENTS MET.")


if __name__ == "__main__":
    check_compliance()
