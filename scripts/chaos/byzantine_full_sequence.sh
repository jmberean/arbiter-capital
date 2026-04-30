#!/usr/bin/env bash
# Chaos: run all 6 Byzantine Watchdog attacks and assert each produces an ATTACK_REJECTED receipt.
set -euo pipefail

DB="$(cd "$(dirname "$0")/../.." && pwd)/axl_network.db"

count_rejections() {
    python - <<PYEOF
import sqlite3, sys
with sqlite3.connect('$DB') as c:
    n = c.execute("SELECT COUNT(*) FROM messages WHERE topic='ATTACK_REJECTED'").fetchone()[0]
print(n)
PYEOF
}

echo "[chaos] Baseline ATTACK_REJECTED count: $(count_rejections)"
BASELINE=$(count_rejections)

echo "[chaos] Launching all 6 Byzantine attacks in sequence (4s apart)..."
python byzantine_watchdog.py --attack-sequence

echo "[chaos] Waiting up to 30s for 6 ATTACK_REJECTED messages..."
python - <<'PYEOF'
import time, sqlite3, json, os, sys
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
BASELINE = int(sys.argv[1]) if len(sys.argv) > 1 else 0
deadline = time.time() + 30
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        n = c.execute("SELECT COUNT(*) FROM messages WHERE topic='ATTACK_REJECTED'").fetchone()[0]
    new = n - BASELINE
    if new >= 6:
        print(f"[chaos] ✓ {new} ATTACK_REJECTED messages received (need 6).")
        sys.exit(0)
    print(f"[chaos] Waiting… {new}/6 rejections so far.")
    time.sleep(2)
print('[chaos] ✗ Did not receive 6 ATTACK_REJECTED messages within 30s.')
sys.exit(1)
PYEOF "$BASELINE"

echo "[chaos] byzantine_full_sequence PASSED"
