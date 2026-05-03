# Arbiter Capital Demo Video Script
# Target: 3 minutes | No music | 720p+ | Show, don't tell

---

## PRE-RECORDING SETUP CHECKLIST
- [ ] Server running: `PYTHONPATH=. python monitor/public_verifier/server.py` → localhost:7777
- [ ] Dashboard open in browser, zoomed to 100%, full-screen Chrome
- [ ] AXL nodes running (or SQLite fallback with `DEMO_MODE=0`)
- [ ] All 5 daemon processes running via `python scripts/start_all.py`
- [ ] Etherscan tab pre-loaded: https://sepolia.etherscan.io/tx/0x21fc3fbc253eae804d0f5f2c19a907fd430231f1acd58725de5c66b049c4f839
- [ ] 0G verifier tab ready (localhost:7777 → /verifier or the 0G Memory Chain panel)
- [ ] Close all notifications, hide dock, set mic to on

---

## VIDEO STRUCTURE

| Part | Duration | What's on screen |
|------|----------|-----------------|
| 1    | 0:00–0:30 | HTML presentation slides 1, 2, 3 |
| 2    | 0:30–2:30 | Live dashboard (localhost:7777) |
| 3    | 2:30–3:00 | HTML presentation slide 11 (close) |

---

## PART 1 SLIDES [0:00–0:30]
**Screen:** `demo/presentation.html` advance through slides 1 → 2 → 3

**Slide 1 (title):**
> "Arbiter Capital is an autonomous yield optimizer for DeFi.
> It continuously runs quantitative analysis across your positions:
> staking yields, Pendle implied rates, volatility.
> When the math says rotate, it gets multi-agent approval and executes on-chain automatically."

**Slide 2 (problem):**
> "Yield opportunities in DeFi are time-sensitive.
> A spread opens on Pendle, stETH yield jumps, ETH volatility spikes.
> By the time you notice and manually execute, the window is gone.
> And if you automate it with a single script, there's nothing checking that script's work."

**Slide 3 (what we built):**
> "Arbiter Capital is five AI agents working together.
> A Quant spots the opportunity, the Risk Guardian checks the math and simulates the trade,
> then two-of-two cryptographic signatures execute it through a Gnosis Safe on Uniswap v4.
> Every decision is logged to 0G decentralised storage. Nothing is a black box."

---

## PART 2 LIVE DEMO [0:30–2:30]
**Screen:** Switch to browser tab with `localhost:7777`

### [0:30–0:45] Show the dashboard
> "This is Mission Control. Five agents, all live."

**[Point to the node panel, 5 green dots]**

> "Quant, Risk Guardian, Executor, Market Oracle, and a Byzantine Watchdog
> we use to test the system's defences."

---

### [0:45–1:05] Inject a scenario
> "Let me trigger a market event."

**[Switch to terminal, run:]**
```
PYTHONPATH=. python apps/market_injector.py flash_crash_eth
```

**[Switch back to dashboard]**

> "ETH just flash-crashed 20%. The Market Oracle broadcast it.
> Watch the Trade Queue."

---

### [1:05–1:45] Watch the card progress
**[Point to the new card appearing in Trade Queue]**

> "A card just appeared. The Quant has proposed swapping WETH to USDC to protect the position."

**[Point to pipeline stages lighting up one by one]**

> "Proposed… the Risk Guardian is evaluating… it called KeeperHub's simulation oracle
> to run the swap on-chain before approving anything.
> Now both agents are signing. EIP-712 signatures. Two of two."

**[Card drops to Completed section]**

> "Executed."

---

### [1:45–2:10] Open the timeline modal
**[Click the completed card]**

> "Every trade has a full decision trail."

**[Scroll slowly through the modal]**

> "The Quant's rationale. The Risk Guardian's evaluation.
> Both signatures. And the on-chain transaction hash at the bottom."

**[Click the tx hash or switch to pre-loaded Etherscan tab]**

> "Confirmed on Sepolia. WETH swapped through Uniswap v4
> via our custom ArbiterThrottleHook, which prevents the fund from front-running itself."

---

### [2:10–2:30] Show threats + 0G panel
**[Switch back to dashboard, point to Threats Blocked panel]**

> "The Byzantine Watchdog fired six adversarial proposals during this run.
> Forged signatures, replayed nonces, math manipulation. All blocked."

**[Point to 0G Memory Chain panel]**

> "And every single AI decision, the full prompt, context, and response,
> is hashed and stored on 0G. 510 receipts deep. Fully replayable."

---

## PART 3 CLOSE [2:30–3:00]
**Screen:** Switch back to `demo/presentation.html`, jump to slide 11

> "Arbiter Capital. Autonomous DeFi for anyone.
> Built on Gensyn AXL, 0G Storage, KeeperHub, and Uniswap v4."

**[Hold on slide for 5 seconds, then fade out]**

---

## RECORDING TIPS
- Speak at ~130 wpm, slower than you think you need to
- Switch browser tabs for the transitions (slides → dashboard → slides)
- If the trade card doesn't appear immediately, wait 10s. Dashboard polls every 5s.
- Record at 1440p, export 1080p minimum
- Target runtime: 2:45–3:10
