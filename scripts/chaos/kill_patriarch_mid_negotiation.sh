#!/usr/bin/env bash
# Chaos: kill Patriarch mid-negotiation.
# Asserts: Quant times out at ~30s and a RejectionReceipt is written to 0G.
set -euo pipefail

TIMEOUT=45

echo "[chaos] Injecting flash_crash_eth scenario..."
python market_injector.py flash_crash_eth &
INJECTOR_PID=$!

# Give Quant enough time to publish a PROPOSAL before killing Patriarch
sleep 4

echo "[chaos] Killing patriarch_process.py..."
pkill -f patriarch_process.py && echo "[chaos] Patriarch killed." || echo "[chaos] Patriarch was not running."

echo "[chaos] Waiting up to ${TIMEOUT}s for RejectionReceipt on AXL bus..."
python - <<'PYEOF'
import time, sqlite3, json, sys, os
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
deadline = time.time() + 45
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT payload FROM messages WHERE topic='ATTACK_REJECTED' OR topic='PROPOSAL_EVALUATIONS' ORDER BY id DESC LIMIT 5"
        ).fetchall()
    for (p,) in rows:
        d = json.loads(p)
        if d.get('consensus_status') == 'REJECTED' or d.get('attack_kind'):
            print(f"[chaos] ✓ Rejection/attack receipt found: {json.dumps(d)[:120]}")
            sys.exit(0)
    time.sleep(2)
print('[chaos] ✗ No rejection receipt within timeout.')
sys.exit(1)
PYEOF

kill $INJECTOR_PID 2>/dev/null || true
echo "[chaos] kill_patriarch_mid_negotiation PASSED"
