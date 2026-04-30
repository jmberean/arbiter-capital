#!/usr/bin/env bash
# Chaos: kill execution_process after it collects exactly one signature, restart,
# assert 2-of-2 completes once and does NOT double-execute.
set -euo pipefail

echo "[chaos] Starting execution_process in background..."
python execution_process.py &
EXEC_PID=$!

echo "[chaos] Injecting scenario..."
python market_injector.py flash_crash_eth

# Wait for one CONSENSUS_SIGNATURES message to appear
python - <<'PYEOF'
import time, sqlite3, os
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
deadline = time.time() + 30
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        cnt = c.execute("SELECT COUNT(*) FROM messages WHERE topic='CONSENSUS_SIGNATURES'").fetchone()[0]
    if cnt >= 1:
        print(f"[chaos] Saw {cnt} CONSENSUS_SIGNATURES — killing executor now.")
        break
    time.sleep(0.5)
PYEOF

kill $EXEC_PID 2>/dev/null && echo "[chaos] Executor killed." || true
sleep 1

echo "[chaos] Restarting execution_process..."
python execution_process.py &
EXEC2_PID=$!

python - <<'PYEOF'
import time, sqlite3, json, os, sys
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
deadline = time.time() + 60
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT payload FROM messages WHERE topic='EXECUTION_SUCCESS' ORDER BY id DESC LIMIT 5"
        ).fetchall()
    if rows:
        txes = {json.loads(p).get('tx_hash') for (p,) in rows}
        if len(txes) == 1:
            print(f"[chaos] ✓ Exactly one EXECUTION_SUCCESS: {txes}")
            sys.exit(0)
        print(f"[chaos] ✗ Multiple distinct execution tx hashes (double-execute?): {txes}")
        sys.exit(1)
    time.sleep(2)
print('[chaos] ✗ No EXECUTION_SUCCESS within timeout.')
sys.exit(1)
PYEOF

kill $EXEC2_PID 2>/dev/null || true
echo "[chaos] kill_executor_after_one_sig PASSED"
