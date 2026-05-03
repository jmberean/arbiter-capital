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

**Thesis:** 4-persona Agent Town over decentralized AXL mesh. No centralized brokers.

*   **AXL Node IDs:**
    *   `Quant_Node_A`
    *   `Patriarch_Node_B`
    *   `Execution_Node_P3`
    *   `KeeperHub_Sim_P4`
    *   `Adversary_Node_Z`
*   **Byzantine Resilience:** 6 forensic `AttackRejection` receipts on 0G:
    * `[PASTE_TX_HASH_A1..A6]`
*   **Transport Enforcement:** See `core/network.py::_assert_demo_transport` which fails-closed if `AXL_NODE_URL` is missing.

---

## 3. Uniswap Foundation — v4 / Unichain ($5,000)

**Thesis:** Custom `ArbiterThrottleHook` for institutional anti-self-MEV.

*   **ArbiterThrottleHook Deployment (Sepolia):** `0x4Fb70855Af455680075d059AD216a01A161800C0`
*   **Deployment Tx:** `0x082752540ff417181607fd41d64e54a69306958aee05d6b2304c86e9c22fa67a`
*   **Etherscan Link:** https://sepolia.etherscan.io/address/0x4Fb70855Af455680075d059AD216a01A161800C0#code
*   **Swap routed through hook:** `[PASTE_SWAP_TX_HASH]`

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
