# Screen Recording Guide — Arbiter Capital Demo

## Scene Order

| # | Duration | What's on screen | What you say |
|---|----------|-----------------|-------------|
| 1 | 0:00–0:18 | Title card (slide 1) or blank with logo | Hook narration |
| 2 | 0:18–0:45 | Dashboard — Mission Control, all 5 nodes alive | "5 agents, Gensyn AXL..." |
| 3 | 0:45–1:10 | Terminal: inject scenario → switch to Trade Queue | "ETH just flash-crashed..." |
| 4 | 1:10–1:45 | Trade Queue card progressing through stages | "Watch these stages..." |
| 5 | 1:45–2:10 | Timeline modal open | "Here's the full audit trail..." |
| 6 | 2:10–2:30 | Etherscan tx page | "Confirmed on Sepolia..." |
| 6b| 2:10–2:30 | OR: 0G Memory Chain panel on dashboard | "Every LLM call stored on 0G..." |
| 7 | 2:30–2:45 | Threats Blocked panel on dashboard | "Byzantine Watchdog..." |
| 8 | 2:45–3:00 | Full dashboard overview | Closing line |

---

## Pre-Flight Checklist

```bash
# Terminal 1 — start daemons (leave running)
PYTHONPATH=. python scripts/start_all.py

# Terminal 2 — start verifier server
PYTHONPATH=. python monitor/public_verifier/server.py

# Browser tab 1
open http://localhost:7777

# Browser tab 2 (pre-load, don't show yet)
open https://sepolia.etherscan.io/tx/0x21fc3fbc253eae804d0f5f2c19a907fd430231f1acd58725de5c66b049c4f839

# Terminal 3 — ready to inject (have this waiting, don't run yet)
PYTHONPATH=. python apps/market_injector.py flash_crash_eth
```

## What to Show in Each Panel

**Mission Control (top-right):**
- Should show: QuantAnalyst, PatriarchAgent, ExecutionAgent, ByzantineWatchdog, MarketGod
- All "alive" (green dot) — if any show offline, wait 30s for next heartbeat

**Trade Queue (left panel):**
- Will be empty before inject
- After inject: card appears within 5–10 seconds, stages light up over ~30-60s

**Threats Blocked (right panel):**
- Shows last 5 attack attempts with "BLOCKED" status
- If empty: inject one of the attack scenarios first to populate it

**0G Memory Chain (bottom-right):**
- Shows audit chain head hash + recent artifact hashes
- If empty: a prior demo run's artifacts may be in 0g_storage/ — they'll show

---

## Terminal Commands to Have Ready (copy-paste)

```bash
# Inject main scenario (show this in video)
PYTHONPATH=. python apps/market_injector.py flash_crash_eth

# Show 0G replay (show command, don't need to wait for output)
PYTHONPATH=. python scripts/replay_decision.py 057e9b56f1e48414e56635875d0532c7ec61a27cc6a2c0ef4d3707f9bdeab403

# Verify audit chain (optional extra)
PYTHONPATH=. python verify_audit.py --walk-from-head
```

---

## Etherscan Links to Have Ready

| What | URL |
|------|-----|
| Main swap (flash_crash_eth) | https://sepolia.etherscan.io/tx/0x21fc3fbc253eae804d0f5f2c19a907fd430231f1acd58725de5c66b049c4f839 |
| ArbiterThrottleHook contract | https://sepolia.etherscan.io/address/0x4Fb70855Af455680075d059AD216a01A161800C0#code |
| Gnosis Safe | https://sepolia.etherscan.io/address/0xd42C17165aC8A2C69f085FAb5daf8939f983eB21 |
| ArbiterReceipt SBT | https://sepolia.etherscan.io/address/0x47D6414fbf582141D4Ce54C3544C14A6057D5a04 |

---

## If Things Go Wrong

**Trade card not appearing after inject:**
- Wait 10s (dashboard polls every 5s)
- Check that server.py is running
- Hard refresh the browser (Cmd+Shift+R)

**Nodes showing "unknown" or "offline":**
- The daemons may not be sending heartbeats if DEMO_MODE=1 and AXL isn't up
- Set DEMO_MODE=0 in .env for local recording, restart daemons

**Card stuck at "proposed":**
- Patriarch may be waiting for LLM response — give it 30-60 seconds
- If still stuck: check patriarch_process terminal for errors

**Modal shows no messages:**
- The session filter is working — if no PROPOSALS message exists for this run, timeline is empty
- Run a full demo run via `python scripts/demo_run.py` to get clean data

---

## Editing Notes

- Cut between scenes at natural pauses (after each sentence ideally)
- Add subtle zoom on the pipeline dots when they light up (Final Cut / Premiere)
- The green "Trade Executed" block in the timeline modal is the visual climax — pause on it for 1-2 seconds
- Keep transitions simple (cut or 0.2s dissolve) — no flashy effects
- Export: H.264, 1080p minimum, 60fps preferred, ~100MB max
