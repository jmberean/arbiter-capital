# Security Threat Model & Mitigations — Arbiter Capital

Arbiter Capital is designed to manage institutional-grade treasury funds autonomously. This requires a "Defense in Depth" approach where no single failure (technical or adversarial) can result in a loss of funds.

## 1. Key Management & Cognitive Isolation

The system splits authority across four distinct keys and processes.

| Key | Role | Exposure Impact | Mitigation |
|---|---|---|---|
| `QUANT_PRIVATE_KEY` | Yield Proposer | Can propose bad trades | Patriarch must sign; 2-of-2 Safe threshold. |
| `PATRIARCH_PRIVATE_KEY` | Risk Auditor | Can sign bad trades | Cannot propose; Quant must also sign. |
| `EXECUTOR_PRIVATE_KEY` | Gas Payer | Liveness failure (no trades) | No Safe authority; cannot move funds. |
| `KEEPERHUB_ATTESTOR_KEY` | Sim Oracle | Can fake sim results | Advisory only; Math + Firewall remain authoritative. |

### 1.1 Cognitive Isolation
The Quant and Patriarch run as separate OS processes with no shared memory or database on the demo path. They communicate exclusively over **Gensyn AXL**, a decentralized P2P mesh. This prevents a single exploit from capturing both keys.

## 2. On-Chain Protection

### 2.1 2-of-2 Gnosis Safe
Funds are held in a Gnosis Safe with a **2-of-2 threshold**. Execution is physically impossible without valid signatures from both the Quant and the Patriarch.

### 2.2 Deterministic Policy Firewall
The Execution Node runs a hardcoded, non-LLM Python firewall (`execution/firewall.py`). Even if both LLMs agree on a trade, the firewall will reject it if:
*   The asset is not in the `WHITELISTED_ASSETS`.
*   The transaction value exceeds `MAX_TRANSACTION_VALUE_USD`.
*   The daily drawdown exceeds `MAX_DAILY_DRAWDOWN_BPS`.
*   The gas price is too high.

### 2.3 ArbiterThrottleHook (Uniswap v4)
Trades route through a custom v4 hook (`ArbiterThrottleHook`) that enforces a cooldown period between trades from the Arbiter Safe. This prevents self-MEV and rapid-fire drain attacks.

## 3. Adversarial Resilience (Byzantine Watchdog)

The system is tested against a **Byzantine Watchdog** — a separate process that publishes corrupted messages to the AXL bus.

| Attack Kind | Mitigation |
|---|---|
| **Invalid Signature** | Signatures are verified using EIP-712 recovery at every step. |
| **Replay Attack** | The `safe_nonce` is included in the signed payload; the Execution Node maintains a `DedupeLedger`. |
| **Math Forgery** | The Patriarch independently re-runs all quantitative tools and rejects on `MATH_MISMATCH`. |
| **Whitelist Bypass** | The Patriarch and Execution Node both enforce the hardcoded whitelist. |
| **Fake Sim Result** | The Patriarch verifies the KeeperHub attestor signature. |
| **Wrong Domain** | The `chainId` and `verifyingContract` are pinned in the EIP-712 domain. |

## 4. Immutable Memory & Auditability

Every decision is hash-chained to **0G Layer 1**.
*   **Tamper-Evidence:** Any change to a past decision breaks the hash chain.
*   **AI Memory Substrate:** Full LLM contexts are stored on-chain, allowing any third party to reproduce and verify the AI's "thought process" using `scripts/replay_decision.py`.
*   **Forensic Logging:** Rejections of Byzantine attacks are recorded on 0G as forensic evidence.

## 5. Deployment Security

*   **Environment Variables:** Secrets are stored in `.env` (excluded from git).
*   **Fail-Closed Transport:** Daemons refuse to start if `AXL_NODE_URL` is missing in demo mode, preventing silent fallback to insecure transport.
*   **Permit2 Bounded Approvals:** We never give `MAX_UINT256` approvals. All Permit2 approvals are bounded and carry a 24-hour expiry.
