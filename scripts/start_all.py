"""
Launch all Arbiter Capital daemons in separate console windows, wait for
them to be ready, then optionally run the full demo or inject a single scenario.

Usage:
  python scripts/start_all.py                  # start daemons, prompt for action
  python scripts/start_all.py --inject flash_crash_eth
  python scripts/start_all.py --demo           # start daemons + run demo_run.py
  python scripts/start_all.py --stop           # kill all running daemons
"""
from __future__ import annotations

import argparse
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
DB_PATH = ROOT / "axl_network.db"
PID_FILE = ROOT / "state" / "daemon_pids.txt"

DAEMONS = [
    ("Quant",     "apps/quant_process.py",       "AXL_NODE_KEY_QUANT"),
    ("Patriarch", "apps/patriarch_process.py",   "AXL_NODE_KEY_PATRIARCH"),
    ("Execution", "apps/execution_process.py",   "AXL_NODE_KEY_EXEC"),
    ("Watchdog",  "apps/byzantine_watchdog.py",  "AXL_NODE_KEY_WATCHDOG"),
    ("Monitor",   "apps/monitor_network.py",     "AXL_NODE_KEY_EXEC"),
]

SCENARIOS = ["flash_crash_eth", "pendle_yield_arbitrage", "protocol_hack",
             "gas_war", "lst_expansion"]


def _col(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _col(t, "92")
def yellow(t): return _col(t, "93")
def red(t):    return _col(t, "91")
def bold(t):   return _col(t, "1")


# ── Daemon management ─────────────────────────────────────────────────────────

def launch_daemon(name: str, script: str, key_env: str) -> subprocess.Popen:
    """Launch a daemon in a new console window. Returns the Popen handle."""
    cmd = [PYTHON, str(ROOT / script)]
    env = os.environ.copy()
    
    # Inject the node-specific key into the child's environment
    if key_env in env:
        env["AXL_NODE_KEY"] = env[key_env]

    kwargs: dict = dict(cwd=str(ROOT), env=env)
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    else:
        # macOS/Linux: redirect output to per-daemon log files
        log_dir = ROOT / "state" / "daemon_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / f"{name.lower()}.log", "a")
        kwargs["stdout"] = log_file
        kwargs["stderr"] = log_file

    proc = subprocess.Popen(cmd, **kwargs)
    return proc


def start_all() -> list[subprocess.Popen]:
    procs = []
    print(bold("\nStarting Arbiter Capital daemons...\n"))
    for name, script, key_env in DAEMONS:
        p = launch_daemon(name, script, key_env)
        procs.append(p)
        print(f"  {green('+')} {name:<12} pid={p.pid}  ({script})")
        time.sleep(0.4)  # slight stagger so logs don't collide at startup

    # Persist PIDs so --stop can find them
    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text("\n".join(str(p.pid) for p in procs))

    return procs


def stop_all():
    if not PID_FILE.exists():
        print(yellow("No PID file found — nothing to stop."))
        return
    pids = [int(x) for x in PID_FILE.read_text().split() if x.strip()]
    killed = 0
    for pid in pids:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                )
                if result.returncode == 0:
                    killed += 1
                    print(f"  {red('-')} killed pid {pid}")
            else:
                os.kill(pid, signal.SIGTERM)
                killed += 1
                print(f"  {red('-')} killed pid {pid}")
        except (ProcessLookupError, PermissionError, OSError):
            pass
    PID_FILE.unlink(missing_ok=True)
    print(f"\nStopped {killed}/{len(pids)} daemons.")


# ── Readiness check ───────────────────────────────────────────────────────────

def _db_count(sql: str, params: tuple = ()) -> int:
    if not DB_PATH.exists():
        return 0
    try:
        with sqlite3.connect(DB_PATH) as c:
            return c.execute(sql, params).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def wait_for_ready(procs: list, timeout: int = 15):
    """Poll until all launched daemon processes are alive."""
    print(yellow("\nWaiting for daemons to start..."))
    deadline = time.time() + timeout
    while time.time() < deadline:
        alive = sum(1 for p in procs if p.poll() is None)
        if alive == len(procs):
            print(green(f"  Ready — {alive}/{len(procs)} daemons running.\n"))
            return True
        print(f"  {alive}/{len(procs)} daemons alive…", end="\r")
        time.sleep(1)
    alive = sum(1 for p in procs if p.poll() is None)
    if alive == len(procs):
        print(green(f"  Ready — {alive}/{len(procs)} daemons running.\n"))
        return True
    print(yellow(f"\n  {alive}/{len(procs)} daemons alive — check state/daemon_logs/ for errors."))
    return False


# ── Scenario injection ────────────────────────────────────────────────────────

def inject(scenario: str):
    print(f"\n{bold('Injecting:')} {scenario}")
    result = subprocess.run(
        [PYTHON, str(ROOT / "apps" / "market_injector.py"), scenario],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(red(f"  market_injector exited {result.returncode}"))


def wait_for_execution(timeout: int = 90) -> str | None:
    baseline = _db_count("SELECT COUNT(*) FROM messages WHERE topic='EXECUTION_SUCCESS'")
    deadline = time.time() + timeout
    print(yellow(f"  Waiting for EXECUTION_SUCCESS (timeout={timeout}s)…"))
    while time.time() < deadline:
        n = _db_count("SELECT COUNT(*) FROM messages WHERE topic='EXECUTION_SUCCESS'")
        if n > baseline:
            try:
                with sqlite3.connect(DB_PATH) as c:
                    row = c.execute(
                        "SELECT payload FROM messages WHERE topic='EXECUTION_SUCCESS' "
                        "ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                import json
                tx = json.loads(row[0]).get("tx_hash", "?") if row else "?"
            except Exception:
                tx = "?"
            print(green(f"  EXECUTION_SUCCESS  tx={tx}"))
            return tx
        time.sleep(2)
    print(red("  Timeout — no EXECUTION_SUCCESS received."))
    return None


# ── Interactive menu ──────────────────────────────────────────────────────────

def interactive_menu():
    print(bold("\n── What would you like to do? ──"))
    print("  1. Inject a scenario")
    print("  2. Run full demo sequence (demo_run.py)")
    print("  3. Run compliance check")
    print("  4. Verify audit chain")
    print("  5. Exit (leave daemons running)")
    print("  0. Stop all daemons and exit")

    choice = input("\n> ").strip()

    if choice == "1":
        print("\nScenarios:")
        for i, s in enumerate(SCENARIOS, 1):
            print(f"  {i}. {s}")
        idx = input("Pick number (or type name): ").strip()
        try:
            scenario = SCENARIOS[int(idx) - 1]
        except (ValueError, IndexError):
            scenario = idx
        inject(scenario)
        wait_for_execution(timeout=90)

    elif choice == "2":
        subprocess.run([PYTHON, str(ROOT / "scripts" / "demo_run.py")], cwd=str(ROOT))

    elif choice == "3":
        subprocess.run([PYTHON, str(ROOT / "scripts" / "check_bounty_compliance.py")],
                       cwd=str(ROOT))

    elif choice == "4":
        subprocess.run([PYTHON, str(ROOT / "apps" / "verify_audit.py"), "--walk-from-head"],
                       cwd=str(ROOT))

    elif choice == "0":
        stop_all()
        sys.exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # Load .env before anything else
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Arbiter Capital launcher")
    parser.add_argument("--inject",  metavar="SCENARIO", help="Inject scenario after startup")
    parser.add_argument("--demo",    action="store_true", help="Run full demo sequence")
    parser.add_argument("--stop",    action="store_true", help="Stop running daemons")
    parser.add_argument("--no-wait", action="store_true", help="Skip readiness check")
    args = parser.parse_args()

    if args.stop:
        stop_all()
        return

    procs = start_all()

    if not args.no_wait:
        wait_for_ready(procs, timeout=15)

    if args.inject:
        inject(args.inject)
        wait_for_execution(timeout=90)
    elif args.demo:
        subprocess.run([PYTHON, str(ROOT / "scripts" / "demo_run.py")], cwd=str(ROOT))
    else:
        # Interactive loop — keep going until user exits
        try:
            while True:
                interactive_menu()
        except KeyboardInterrupt:
            print("\n\nExiting menu (daemons still running in their windows).")
            print(f"To stop all:  python scripts/start_all.py --stop")


if __name__ == "__main__":
    main()
