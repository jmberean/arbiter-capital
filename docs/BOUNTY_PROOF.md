# Bounty Proof — Arbiter Capital

This document provides explicit evidence for each bounty targeted by Arbiter Capital.

## 1. 0G — "Bringing AI fully on-chain" ($15,000)

**Thesis:** 0G as the canonical AI memory substrate. Every LLM call is cryptographically reproducible.

*   **Audit Chain Head (0G Tx):** `[PASTE_TX_HASH_HERE]`
*   **LLMContext Artifacts (>=6):**
    1. `[PASTE_TX_HASH_1]`
    2. `[PASTE_TX_HASH_2]`
    3. `[PASTE_TX_HASH_3]`
    4. `[PASTE_TX_HASH_4]`
    5. `[PASTE_TX_HASH_5]`
    6. `[PASTE_TX_HASH_6]`
*   **DecisionReceipts (>=3):**
    1. `[PASTE_TX_HASH_7]`
    2. `[PASTE_TX_HASH_8]`
    3. `[PASTE_TX_HASH_9]`
*   **Replay Evidence:**
    ```bash
    python scripts/replay_decision.py --tx [PASTE_TX_HASH_1]
    # Output: ✓ DETERMINISTIC MATCH — decision is verifiable
    ```
*   **Public Verifier:** [PASTE_VERIFIER_URL_HERE]

---

## 2. Gensyn — "Best Application of AXL" ($5,000)

**Thesis:** 5-persona Agent Town over a live Yggdrasil/AXL mesh. No centralized brokers.

*   **AXL Nodes (5 distinct Yggdrasil identities, hub-spoke topology):**
    *   `quant`      — API :9011, hub node (Listen tls://127.0.0.1:9021)
    *   `patriarch`  — API :9012, spoke
    *   `exec`       — API :9013, spoke
    *   `keeperhub`  — API :9014, spoke
    *   `watchdog`   — API :9015, spoke (Byzantine adversary)
*   **Transport verification:** `core/network.py` uses real AXL `/send` + `/recv` endpoints; `DEMO_MODE=1` fails-closed if any `AXL_NODE_URL_*` is unreachable.
*   **Byzantine Resilience:** Byzantine Watchdog publishes adversarial proposals; Patriarch + firewall reject them with signed `AttackRejection` receipts logged to 0G.
*   **Setup:** `bash scripts/setup_axl.sh` — starts all 5 nodes, captures pubkeys via `/topology`, writes `AXL_PEER_KEYS` to `.env`.

---

## 3. Uniswap Foundation — v4 / Unichain ($5,000)

**Thesis:** Custom `ArbiterThrottleHook` for institutional anti-self-MEV.

*   **ArbiterThrottleHook Deployment (Sepolia):** `0x4Fb70855Af455680075d059AD216a01A161800C0`
*   **Deployment Tx:** `0x082752540ff417181607fd41d64e54a69306958aee05d6b2304c86e9c22fa67a`
*   **Etherscan Link:** https://sepolia.etherscan.io/address/0x4Fb70855Af455680075d059AD216a01A161800C0#code
*   **End-to-end Safe execution tx (Sepolia):** `0x4b48ee7f` — 2-of-2 multisig threshold met, UR calldata with ArbiterThrottleHook, GS026-clean
*   **Root cause fixed:** Non-deterministic Permit2 expiry (caller-supplied `deadline` now propagated end-to-end so `safe_tx_hash` is identical at signing and submission)

---

## 4. KeeperHub — "Best Use of KeeperHub" ($4,500)

**Thesis:** KeeperHub as a consensus-time Simulation Oracle (F1) and public LangChain bridge (F2).

*   **Safe Module Enable Tx:** `0x7cd80e05dbb594f70cf6439c168817eb873d9b12811c4a988049a10a01a3f30b`
*   **Sim Oracle Invocations (>=3):**
    1. `[PASTE_TX_OR_LOG_REF]`
*   **LangChain Bridge:** `langchain_keeperhub.py` implemented as a reusable `BaseTool`.

---

## 5. KeeperHub — "Builder Feedback" ($500)

*   **Feedback Document:** [docs/KEEPERHUB_FEEDBACK.md](docs/KEEPERHUB_FEEDBACK.md)
*   **Actionable items:** 3 friction points, 1 documentation gap.
