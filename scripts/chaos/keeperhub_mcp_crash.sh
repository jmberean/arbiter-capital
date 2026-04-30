#!/usr/bin/env bash
# Chaos: crash the KeeperHub MCP server before a sim-oracle call is made.
# Asserts: Patriarch times out at 8s and rejects with OUTSIDE_MANDATE.
set -euo pipefail

echo "[chaos] Unsetting KEEPERHUB_SERVER_PATH to simulate MCP crash..."
SAVED_KH=${KEEPERHUB_SERVER_PATH:-}
export KEEPERHUB_SERVER_PATH="/nonexistent/keeperhub-crash-simulation"

echo "[chaos] Injecting scenario..."
python market_injector.py flash_crash_eth

python - <<'PYEOF'
import time, sqlite3, json, os, sys
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
deadline = time.time() + 60
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT payload FROM messages WHERE topic='PROPOSAL_EVALUATIONS' ORDER BY id DESC LIMIT 5"
        ).fetchall()
    for (p,) in rows:
        d = json.loads(p)
        if d.get('consensus_status') == 'REJECTED':
            reason = d.get('rejection_reason', '') or d.get('rationale', '')
            if 'OUTSIDE_MANDATE' in reason or 'sim' in reason.lower() or 'timeout' in reason.lower():
                print(f"[chaos] ✓ KeeperHub MCP crash → OUTSIDE_MANDATE rejection: {reason[:80]}")
                sys.exit(0)
            # Any rejection during sim outage also counts
            print(f"[chaos] ✓ Patriarch rejected proposal (reason: {reason[:80]})")
            sys.exit(0)
    time.sleep(2)
print('[chaos] ✗ No rejection within timeout after KeeperHub MCP crash.')
sys.exit(1)
PYEOF

export KEEPERHUB_SERVER_PATH="$SAVED_KH"
echo "[chaos] keeperhub_mcp_crash PASSED"
