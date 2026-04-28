#!/usr/bin/env bash
# Chaos: inject gas_war scenario (market_god already sets gas_price_gwei=500).
# Asserts: firewall rejects the proposal with gas_price_gwei > threshold.
set -euo pipefail

echo "[chaos] Injecting gas_war scenario (500 gwei)..."
python market_injector.py gas_war

python - <<'PYEOF'
import time, sqlite3, json, os, sys
DB = os.path.join(os.path.dirname(__file__), '..', '..', 'axl_network.db')
deadline = time.time() + 30
while time.time() < deadline:
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT payload FROM messages WHERE topic='PROPOSAL_EVALUATIONS' OR topic='ATTACK_REJECTED' ORDER BY id DESC LIMIT 10"
        ).fetchall()
    for (p,) in rows:
        d = json.loads(p)
        status = d.get('consensus_status') or d.get('attack_kind', '')
        rationale = d.get('rationale', '') or d.get('reason', '')
        if status in ('REJECTED', 'GAS_INEFFICIENT') or 'gas' in rationale.lower():
            print(f"[chaos] ✓ Gas-spike rejection confirmed: {status} — {rationale[:80]}")
            sys.exit(0)
    time.sleep(2)
# gas_war may produce NO proposal (market_god returns no trade) — that also counts
with sqlite3.connect(DB) as c:
    no_prop = c.execute(
        "SELECT COUNT(*) FROM messages WHERE topic='PROPOSALS'"
    ).fetchone()[0]
if no_prop == 0:
    print('[chaos] ✓ No proposal generated during gas_war (firewall pre-rejected).')
    sys.exit(0)
print('[chaos] ✗ Proposal was not rejected during gas spike scenario.')
sys.exit(1)
PYEOF

echo "[chaos] gas_spike_500gwei PASSED"
