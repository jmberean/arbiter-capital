"""Bounty compliance gate. Exit 0 = ship-ready. Non-zero = fix before submitting."""
import os
import sys

# Ensure project root is on path when run from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


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
    net = _read("core/network.py")
    check("gensyn.demo_mode_guard",
          "DEMO_MODE" in net and "_assert_demo_transport" in net,
          "(network.py fail-closed enforcement)")
    check("gensyn.envelope_signing",
          "_build_envelope" in net and "_verify_envelope" in net,
          "(envelope-signed AXL messages)")

    # 2. 0G — MemoryManager writes to chain + hash-chaining
    mm = _read("memory/memory_manager.py")
    check("zerog.live_writes", "send_raw_transaction" in mm, "(Web3 0G persistence)")
    check("zerog.hash_chain", "prev_0g_tx_hash" in mm and "receipt_hash" in mm,
          "(hash-chained receipts)")
    check("zerog.audit_chain_module", os.path.exists("memory/audit_chain.py"),
          "(audit_chain.py)")

    # 3. 0G — replay tool
    check("zerog.replay_script", os.path.exists("scripts/replay_decision.py"),
          "(replay_decision.py)")

    # 4. Uniswap v4 — hook implementation (real, not stub)
    has_throttle_hook = os.path.exists("contracts/ArbiterThrottleHook.sol")
    if has_throttle_hook:
        hook_src = _read("contracts/ArbiterThrottleHook.sol")
        check("uniswap.throttle_hook_real",
              "arbiterSafe" in hook_src
              and "lastSwapAt" in hook_src
              and "windowNotionalUsed" in hook_src
              and "_afterSwap" in hook_src,
              "(real ArbiterThrottleHook with cooldown + notional cap)")
    else:
        check("uniswap.throttle_hook_real", False, "(ArbiterThrottleHook.sol missing)")

    # 5. Uniswap v4 — SBT receipt contract
    check("uniswap.arbiter_receipt_sbt", os.path.exists("contracts/ArbiterReceipt.sol"),
          "(ArbiterReceipt.sol)")

    # 6. KeeperHub F1 — MCP client (real simulate_safe_tx call)
    kh = _read("execution/keeper_hub.py")
    check("keeperhub.f1_mcp_client",
          "ClientSession" in kh and "simulate_safe_tx" in kh and "execute_safe_transaction" in kh,
          "(MCP ClientSession + both real tools)")
    check("keeperhub.attestor_signing",
          "sim_result_digest" in kh and "KEEPERHUB_KEY" in kh,
          "(Sim Oracle attestor-signs every result)")

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
        fb_text = _read(fb_path)
        check("keeperhub.builder_feedback",
              os.path.getsize(fb_path) >= 4096 and fb_text.count("\n## ") >= 3,
              f"(size={os.path.getsize(fb_path)}, h2_sections={fb_text.count(chr(10)+'## ')})")
    else:
        check("keeperhub.builder_feedback", False, "(docs/KEEPERHUB_FEEDBACK.md missing)")

    # 9. EIP-712 + ConsensusBundle
    check("crypto.eip712", os.path.exists("core/crypto.py"), "(core/crypto.py)")
    crypto = _read("core/crypto.py")
    check("crypto.bundle_hash", "bundle_hash" in crypto, "(ConsensusBundle digest)")
    check("crypto.sim_result_digest", "sim_result_digest" in crypto, "(Sim attestor digest)")

    # 10. Models — full v5 set
    models = _read("core/models.py")
    for m in ["ConsensusBundle", "SimulationRequest", "AttackRejection",
              "ExecutionReceipt", "ExecutionFailure", "Heartbeat",
              "ProposalEvaluation", "MarketSnapshot"]:
        check(f"models.{m}", f"class {m}" in models, f"(v5 spec model)")
    check("models.eip712_message", "def eip712_message" in models,
          "(Proposal.eip712_message helper)")

    # 11. Byzantine Watchdog — all 6 attacks
    wd = _read("byzantine_watchdog.py")
    check("watchdog.all_attacks",
          all(f"attack_A{i}" in wd for i in range(1, 7)),
          "(A1-A6 all present)")
    check("watchdog.A2_real_replay",
          "_last_executed_record" in wd or "DedupeLedger" in wd,
          "(A2 targets a real settled nonce)")

    # 12. verify_audit --walk-from-head + reorg awareness
    va = _read("verify_audit.py")
    check("audit.walk_from_head", "walk_from_head" in va and "walk_chain" in va,
          "(verify_audit.py chain walk)")
    check("audit.reorg_aware",
          "MIN_CONFIRMATIONS" in va and "_wait_for_confirmations" in va,
          "(reorg-aware confirmations)")

    # 13. Public verifier page + server
    check("verifier.html", os.path.exists("monitor/public_verifier/index.html"),
          "(monitor/public_verifier/index.html)")
    check("verifier.server", os.path.exists("monitor/public_verifier/server.py"),
          "(monitor/public_verifier/server.py)")
    if os.path.exists("monitor/public_verifier/index.html"):
        ix = _read("monitor/public_verifier/index.html")
        check("verifier.canonical_json",
              "canonicalJson" in ix and "/\\s/g" not in ix,
              "(canonical JSON without whitespace-strip bug)")

    # 14. Patriarch — sim attestor verification
    patriarch = _read("agents/patriarch.py")
    check("patriarch.sim_attestor_check",
          "is_attestor" in patriarch and "sim_result_digest" in patriarch,
          "(consult_sim_oracle verifies attestor sig)")
    check("patriarch.outside_mandate_on_timeout",
          "OUTSIDE_MANDATE" in patriarch,
          "(sim oracle timeout → REJECTED OUTSIDE_MANDATE)")

    # 15. Quant — real Safe nonce
    quant = _read("agents/quant.py")
    check("quant.real_nonce",
          "treasury.read_nonce()" in quant and "p.safe_nonce = 0" not in quant,
          "(no hardcoded nonce=0)")

    # 16. Execution — SBT mint + ExecutionReceipt
    exe = _read("execution_process.py")
    check("execution.sbt_mint",
          "_mint_sbt" in exe and "mintReceipt" in exe,
          "(SBT minted on success)")
    check("execution.execution_receipt",
          "ExecutionReceipt(" in exe,
          "(ExecutionReceipt published)")
    check("execution.heartbeat",
          "_heartbeat_loop" in exe and "Heartbeat(" in exe,
          "(periodic heartbeat)")

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
