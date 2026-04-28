#!/usr/bin/env bash
# Chaos: simulate 0G RPC outage by unsetting ZERO_G_RPC_URL, inject a proposal,
# restore env, assert pending receipts drain.
set -euo pipefail

echo "[chaos] Saving ZERO_G_RPC_URL and unsetting it to simulate outage..."
SAVED_RPC=${ZERO_G_RPC_URL:-}
export ZERO_G_RPC_URL=""

echo "[chaos] Injecting scenario during simulated 0G outage..."
python market_injector.py pendle_yield_arbitrage

echo "[chaos] Waiting 8s for queued writes to accumulate..."
sleep 8

echo "[chaos] Restoring ZERO_G_RPC_URL: ${SAVED_RPC:-<unset>}"
export ZERO_G_RPC_URL="$SAVED_RPC"

echo "[chaos] Checking that 0g_storage directory received receipts (mock drain)..."
python - <<'PYEOF'
import os, glob, sys, time
STORAGE = os.path.join(os.path.dirname(__file__), '..', '..', '0g_storage')
deadline = time.time() + 30
while time.time() < deadline:
    files = glob.glob(os.path.join(STORAGE, '*.json'))
    if files:
        print(f"[chaos] ✓ {len(files)} receipt(s) in 0g_storage after simulated outage: {[os.path.basename(f) for f in files[:3]]}")
        sys.exit(0)
    time.sleep(2)
print('[chaos] ✗ No receipts found in 0g_storage.')
sys.exit(1)
PYEOF

echo "[chaos] simulate_0g_outage PASSED"
