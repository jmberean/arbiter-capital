"""
Demo orchestration script — drives the recording in one command.

Each step injects a scenario or runs an action, then polls the AXL SQLite bus
until the expected event arrives (or timeout expires, aborting with a clear error).

Usage:
  python scripts/demo_run.py
  python scripts/demo_run.py --skip-watchdog
  python scripts/demo_run.py --dry-run
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "axl_network.db"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _db_count(sql: str, params: tuple = ()) -> int:
    if not DB_PATH.exists():
        return 0
    with sqlite3.connect(DB_PATH) as c:
        return c.execute(sql, params).fetchone()[0]


def inject(scenario: str):
    """Run market_injector.py in a subprocess (non-blocking — the daemon processes do the work)."""
    print(f"  → inject {scenario}")
    subprocess.run([sys.executable, str(ROOT / "market_injector.py"), scenario], check=True)


def wait_for(description: str, predicate, timeout_s: int, poll_s: float = 1.5):
    """Block until predicate() is truthy, or abort on timeout."""
    deadline = time.time() + timeout_s
    print(f"  ⏳ Waiting for: {description} (timeout={timeout_s}s)")
    while time.time() < deadline:
        result = predicate()
        if result:
            print(f"  ✓ {description}")
            return result
        time.sleep(poll_s)
    print(f"  ✗ TIMEOUT waiting for: {description}")
    sys.exit(1)


def baseline(topic: str) -> int:
    return _db_count("SELECT COUNT(*) FROM messages WHERE topic=?", (topic,))


# ── Step definitions ─────────────────────────────────────────────────────────

def step_inject_and_execute(scenario: str, timeout: int = 90) -> str:
    """Inject a market scenario and wait for EXECUTION_SUCCESS."""
    b = baseline("EXECUTION_SUCCESS")
    inject(scenario)
    def got_exec():
        n = _db_count("SELECT COUNT(*) FROM messages WHERE topic='EXECUTION_SUCCESS'")
        return n > b
    wait_for(f"EXECUTION_SUCCESS after {scenario}", got_exec, timeout)
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute(
            "SELECT payload FROM messages WHERE topic='EXECUTION_SUCCESS' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    tx = json.loads(row[0]).get("tx_hash", "?") if row else "?"
    print(f"  tx_hash={tx}")
    return tx


def step_watchdog_sequence(timeout: int = 35):
    """Run all 6 Byzantine attacks and assert 6 ATTACK_REJECTED receipts appear."""
    b = baseline("ATTACK_REJECTED")
    print("  → byzantine_watchdog --attack-sequence")
    subprocess.Popen([sys.executable, str(ROOT / "byzantine_watchdog.py"), "--attack-sequence"])
    def got_six():
        n = _db_count("SELECT COUNT(*) FROM messages WHERE topic='ATTACK_REJECTED'")
        new = n - b
        print(f"     {new}/6 rejections…", end="\r")
        return new >= 6
    wait_for("6 ATTACK_REJECTED messages", got_six, timeout)
    print()


def step_replay(proposal_id: str, timeout: int = 30):
    """Run replay_decision.py for the most recent LLMContext tx hash."""
    # Find the latest LLMContext receipt tx hash from 0g_storage
    storage = ROOT / "0g_storage"
    ctx_files = sorted(storage.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    tx_hash = None
    for f in ctx_files:
        try:
            d = json.loads(f.read_text())
            if d.get("receipt_type") == "LLMContext":
                tx_hash = f.stem
                break
        except Exception:
            continue
    if not tx_hash:
        print("  ⚠ No LLMContext receipt found — skipping replay step.")
        return
    print(f"  → replay_decision.py --tx {tx_hash}")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "replay_decision.py"), "--tx", tx_hash],
        capture_output=True, text=True, timeout=timeout,
    )
    print(result.stdout[-400:] if result.stdout else "(no output)")
    if result.returncode != 0:
        print(f"  ⚠ replay exited {result.returncode}: {result.stderr[-200:]}")


def step_verify_chain(min_receipts: int = 12, timeout: int = 30):
    """Run verify_audit.py --walk-from-head and assert CHAIN VERIFIED."""
    print("  → verify_audit.py --walk-from-head")
    result = subprocess.run(
        [sys.executable, str(ROOT / "verify_audit.py"), "--walk-from-head"],
        capture_output=True, text=True, timeout=timeout,
    )
    output = result.stdout + result.stderr
    print(output[-600:])
    if "CHAIN VERIFIED" not in output:
        print("  ✗ Chain verification FAILED")
        sys.exit(1)
    # Extract receipt count
    for line in output.splitlines():
        if "CHAIN VERIFIED" in line:
            print(f"  ✓ {line.strip()}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Arbiter Capital demo orchestration")
    parser.add_argument("--skip-watchdog", action="store_true", help="Skip Byzantine Watchdog sequence")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    args = parser.parse_args()

    if args.dry_run:
        steps = [
            "inject flash_crash_eth → wait EXECUTION_SUCCESS (60s)",
            "inject pendle_yield_arbitrage → wait EXECUTION_SUCCESS (90s)",
            "watchdog --attack-sequence → wait 6 ATTACK_REJECTED (35s)",
            "inject protocol_hack → wait EXECUTION_SUCCESS (30s)",
            "inject gas_war → wait EXECUTION_SUCCESS or no-proposal (20s)",
            "replay latest LLMContext from 0g_storage",
            "verify_audit --walk-from-head → CHAIN VERIFIED ≥12",
        ]
        print("Demo steps (dry-run):")
        for i, s in enumerate(steps, 1):
            print(f"  {i}. {s}")
        return

    total_start = time.time()
    print("=" * 60)
    print("Arbiter Capital Demo Orchestration — START")
    print("=" * 60)

    print("\n[1/7] Inject flash_crash_eth")
    step_inject_and_execute("flash_crash_eth", timeout=60)

    print("\n[2/7] Inject pendle_yield_arbitrage (2 iterations)")
    step_inject_and_execute("pendle_yield_arbitrage", timeout=90)

    if not args.skip_watchdog:
        print("\n[3/7] Byzantine Watchdog — 6 attacks")
        step_watchdog_sequence(timeout=35)
    else:
        print("\n[3/7] Skipping Watchdog (--skip-watchdog)")

    print("\n[4/7] Inject protocol_hack")
    step_inject_and_execute("protocol_hack", timeout=30)

    print("\n[5/7] Inject gas_war (firewall or market_god should reject)")
    gas_b = baseline("EXECUTION_SUCCESS")
    inject("gas_war")
    time.sleep(20)
    gas_n = _db_count("SELECT COUNT(*) FROM messages WHERE topic='EXECUTION_SUCCESS'")
    if gas_n > gas_b:
        print("  ✓ Executed (gas within threshold)")
    else:
        print("  ✓ No execution (firewall/market_god rejected gas_war — expected)")

    print("\n[6/7] Replay latest LLMContext decision")
    step_replay("latest", timeout=30)

    print("\n[7/7] Verify audit chain")
    step_verify_chain(min_receipts=12, timeout=30)

    elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"Demo completed in {elapsed:.0f}s ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
