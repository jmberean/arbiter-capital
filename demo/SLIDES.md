# Arbiter Capital — Slide Deck Content
# Use this to build your PowerPoint / Keynote / Google Slides
# Suggested: dark background (#0F1117), accent colors: blue (#3B82F6), emerald (#10B981), amber (#F59E0B)

---

## SLIDE 1 — Title

**ARBITER CAPITAL**
Autonomous Multi-Agent DeFi Treasury

*ETHGlobal Open Agents 2026*

[Subtitle: Gensyn AXL · 0G Storage · KeeperHub · Uniswap v4]

---

## SLIDE 2 — The Problem (1 sentence each, no bullets)

**DeFi treasuries face three unsolved problems:**

1. AI decisions are a black box — no audit trail, no replay
2. Single agents have no checks — one compromised node moves the fund
3. On-chain execution is blind — no simulation before signing

---

## SLIDE 3 — What We Built

**An autonomous treasury where AI agents negotiate, verify, and sign every trade.**

```
Market Signal
     ↓
Quant Analyst        (LangGraph + EIP-712)
     ↓  [Gensyn AXL]
Risk Guardian        (LangGraph + KeeperHub Sim Oracle)
     ↓
Trade Executor       (2-of-2 Safe → Uniswap v4)
     ↓
0G Storage           (every LLM call hashed & chained)
```

Byzantine Watchdog fires adversarial proposals in parallel — all rejected.

---

## SLIDE 4 — Architecture Diagram

[Use this ASCII or recreate as a visual diagram]

```
                    ┌─────────────────────────────┐
                    │      Gensyn AXL Mesh         │
                    │  (5 Yggdrasil P2P nodes)     │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌─────────────┐    ┌───────────────┐    ┌──────────────┐
   │   QUANT     │    │  PATRIARCH    │    │   EXECUTOR   │
   │  Analyst    │───▶│ Risk Guardian │───▶│  Trade Exec  │
   │ LangGraph   │    │  LangGraph    │    │  Gnosis Safe │
   └──────┬──────┘    └──────┬────────┘    └──────┬───────┘
          │                  │                    │
          ▼                  ▼                    ▼
   ┌─────────────────────────────────────────────────────┐
   │                  0G Decentralised Storage            │
   │   LLMContext artifacts · DecisionReceipts · Chain   │
   └─────────────────────────────────────────────────────┘
                               ▲
                    ┌──────────┴───────────┐
                    │  Byzantine Watchdog  │
                    │  (adversary agent)   │
                    └──────────────────────┘
```

---

## SLIDE 5 — Live Demo Preview (screenshot)

[Insert screenshot of your dashboard here]

Caption: *Mission Control dashboard — real-time agent status, trade queue, threat log, 0G audit chain*

---

## SLIDE 6 — Trade Flow (numbered steps)

**A trade from signal to settlement:**

1. **Market Oracle** broadcasts flash crash event over AXL
2. **Quant** runs LangGraph pipeline → drafts swap proposal → EIP-712 signs
3. **Patriarch** re-runs quant math → calls KeeperHub Sim Oracle (simulates on-chain) → approves → signs
4. **Executor** ecrecovers both signatures → confirms 2-of-2 threshold → calls `Safe.execTransaction`
5. **Uniswap v4** routes swap through `ArbiterThrottleHook` (anti-MEV per-block rate limit)
6. **0G** stores full LLM context for both agents → audit receipt minted → chained to prior head

---

## SLIDE 7 — Bounty Highlights

| Bounty | What We Built |
|--------|--------------|
| **Gensyn AXL** ($5k) | 5-node Yggdrasil mesh, DEMO_MODE fails-closed without real AXL, Byzantine Watchdog |
| **0G Storage** ($15k) | LLMContext artifacts, 510-receipt audit chain, replay CLI |
| **KeeperHub** ($4.5k) | Sim Oracle at consensus time, LangChain BaseTool bridge |
| **Uniswap v4** ($5k) | ArbiterThrottleHook deployed Sepolia, 3 live swap txns |

---

## SLIDE 8 — Deployed Contracts (Sepolia)

| Contract | Address |
|----------|---------|
| Gnosis Safe (2-of-2) | `0xd42C17165aC8A2C69f085FAb5daf8939f983eB21` |
| ArbiterThrottleHook | `0x4Fb70855Af455680075d059AD216a01A161800C0` |
| ArbiterReceipt SBT | `0x47D6414fbf582141D4Ce54C3544C14A6057D5a04` |

**Live swap transactions (Sepolia):**
- flash_crash_eth WETH→USDC: `0x21fc3fbc...4f839`
- gas_war WETH→USDC: `0xd725285f...035e`
- pendle_yield_arb: `0x399ac5a3...460`

---

## SLIDE 9 — 0G Audit Chain

**Every LLM call is reproducible:**

```
sha256( system_prompt + messages + model_id + temperature + seed )
                        ↓
              LLMContext artifact → 0G hash
                        ↓
         chained: receipt_hash = sha256( payload + prev_hash )
```

Audit chain depth: **510+ receipts**
Head: `0c21b299bf0b339a5eedda9296407424baa3afaf5e37bf839b7574f1e1d73da8`

Replay: `python scripts/replay_decision.py <hash>`
→ Pulls artifact from 0G, reruns call, verifies schema-bound response hash

---

## SLIDE 10 — Byzantine Resilience

**6 attack types blocked every demo run:**

| Attack | Method | Blocked By |
|--------|--------|-----------|
| A1: Invalid signature | Forged quant sig | ecrecover mismatch |
| A2: Replay nonce | Stale safe_tx_hash | Nonce check |
| A3: Math forge | Manipulated amount | Hash mismatch in recheck |
| A4: Whitelist bypass | Unknown protocol | Firewall |
| A5: Fake sim oracle | Unsigned attestation | Sig verification |
| A6: Wrong domain | Bad EIP-712 domain | ecrecover mismatch |

Every rejection is signed and logged to 0G with an `AttackRejection` receipt.

---

## SLIDE 11 — Close

**Arbiter Capital**

*Transparent · Byzantine-Resilient · Fully Auditable*

GitHub: [your repo]
Verifier: [your deployed URL or localhost:7777]

Built in 48 hours at ETHGlobal Open Agents 2026

---

## DESIGN NOTES

**Colors:**
- Background: `#0F1117` (near-black)
- Primary text: `#F8FAFC`
- Blue accent (Quant/AXL): `#3B82F6`
- Emerald accent (executed/success): `#10B981`
- Amber accent (evaluating): `#F59E0B`
- Rose accent (attacks): `#F43F5E`
- Violet accent (0G): `#8B5CF6`

**Font:** Use a monospace font (JetBrains Mono or Fira Code) for addresses/hashes. Sans-serif (Inter or similar) for body text.

**Slide count:** 11 slides. For a 3-min video you won't show slides — use them as a backdrop for your intro/close title cards only. The live demo is the main content.
