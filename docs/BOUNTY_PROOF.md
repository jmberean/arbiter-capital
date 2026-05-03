# Bounty Proof — Arbiter Capital

This document provides explicit evidence for each bounty targeted by Arbiter Capital.

## 1. 0G — "Bringing AI fully on-chain" ($15,000)

**Thesis:** 0G as the canonical AI memory substrate. Every LLM call is cryptographically reproducible.

*   **Audit Chain Head (local 0G hash):** `0c21b299bf0b339a5eedda9296407424baa3afaf5e37bf839b7574f1e1d73da8`
*   **LLMContext Artifacts (6 most recent — Quant + Patriarch decision calls):**
    1. `057e9b56f1e48414e56635875d0532c7ec61a27cc6a2c0ef4d3707f9bdeab403`
    2. `e4dc9e733de4da288ea2cdd6b4dda6f0fe61c55afd8b66135d509edb02e875e3`
    3. `36baad7708aefe2bef2af132db368414f371bd06c35354c1da8ed52aadcf3793`
    4. `71c205b3b858d6e5b61dd7313c98eec2cec959de95bd98cb0190360b045080f0`
    5. `8b1169f166bce934427efe8863ad9d59f937a0b3a186ab42d892e0abb0e59bdf`
    6. `c463736e8ad8399d9b81de60c13fc7fd6c881a5761d7be081e83903ce436d6c5`
*   **DecisionReceipts (3 most recent):**
    1. `2e0849d27d7d4c0713c0f04e7b9602bd4873b6de35d8831a6db5f45f5d6e1995`
    2. `7cddfdf710ab1e320e25c2fc4c0bc32b66c38f606ad3be3164149f10f541f08c`
    3. `6de904ad9dad83b35308e232f49b5851045da5af64b07d6e9e05cdb994536132`
*   **ExecutionReceipts (3 most recent):**
    1. `c1f72964b51dc7de93579ca7f1b1f138ddefb75f2ce7b2739b75569eed3ffe9d`
    2. `14c9d687db4a700498f2903b2721f56a6c7dae6a5aaf78008730e754fc2de0fb`
    3. `4d689255af9d2ce2b959505c2cd617f1d228721c7bfc93dc604bf00b91165c66`
*   **Audit chain depth:** 510+ receipts verified (`apps/verify_audit.py --walk-from-head` → `CHAIN VERIFIED`)
*   **Replay Evidence:**
    ```bash
    python scripts/replay_decision.py --tx 057e9b56f1e48414e56635875d0532c7ec61a27cc6a2c0ef4d3707f9bdeab403
    # Output: ⚠ Raw response differs (expected at temperature > 0).
    #         The schema-bound parsed_hash is the canonical reproducibility proof.  ✓ exit 0
    ```
*   **Public Verifier:** `monitor/public_verifier/index.html` (served by `monitor/public_verifier/server.py`)

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
*   **Byzantine Resilience:** Byzantine Watchdog fires 6 adversarial proposals per demo run (A1–A6: invalid sig, replay nonce, math forge, whitelist bypass, fake sim, wrong domain); Patriarch + firewall reject all 6 with signed `AttackRejection` receipts logged to 0G.
*   **Setup:** `bash scripts/setup_axl.sh` — starts all 5 nodes, captures pubkeys via `/topology`, writes `AXL_PEER_KEYS` to `.env`.

---

## 3. Uniswap Foundation — v4 / Unichain ($5,000)

**Thesis:** Custom `ArbiterThrottleHook` for institutional anti-self-MEV.

*   **ArbiterThrottleHook Deployment (Sepolia):** `0x4Fb70855Af455680075d059AD216a01A161800C0`
*   **Deployment Tx:** `0x082752540ff417181607fd41d64e54a69306958aee05d6b2304c86e9c22fa67a`
*   **Etherscan Link:** https://sepolia.etherscan.io/address/0x4Fb70855Af455680075d059AD216a01A161800C0#code
*   **End-to-end Safe SWAP execution txns (Sepolia, 2-of-2 multisig):**
    *   `flash_crash_eth` SWAP (WETH→USDC, nonce=29): `0x21fc3fbc253eae804d0f5f2c19a907fd430231f1acd58725de5c66b049c4f839`
    *   `gas_war` SWAP (WETH→USDC, nonce=31): `0xd725285ff0857ce63b70f975ff805862ae7260a40d2fd672f30991ab26df035e`
    *   `pendle_yield_arbitrage` SWAP (nonce=27): `0x399ac5a34a5a3f0a3a65cc69d244522c18cd9a3bf7424fc86c8174c0d19a3460`
*   **SBT receipts minted per execution:**
    *   nonce=29 SBT: `41e848b19a0e307184b0f3f4aa10145b3bd4136ac0febd82f1fcaaaa661f947f`
    *   nonce=30 SBT: `ad3675e9bf4223158f0ee2d29ea26fabf3ea1c6da15ec4d02abdc1db78e73391`
    *   nonce=31 SBT: `d6025509eafed75c134fdf867816ef68ac2f08deedbd1a0bc19e9b17d13c9ba4`
*   **Root cause fixed:** Non-deterministic Permit2 expiry (caller-supplied `deadline` now propagated end-to-end so `safe_tx_hash` is identical at signing and submission)

---

## 4. KeeperHub — "Best Use of KeeperHub" ($4,500)

**Thesis:** KeeperHub as a consensus-time Simulation Oracle (F1) and public LangChain bridge (F2).

*   **Safe Module Enable Tx:** `0x7cd80e05dbb594f70cf6439c168817eb873d9b12811c4a988049a10a01a3f30b`
*   **Sim Oracle Invocations (10+ during demo run, attestor `0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D`):**
    1. `emergency_withdraw_001` — execution tx `0x2812dfb7be343181c8d7ca898d5c8de96e41c167f82fe20fb8325648159486d4` (nonce=26)
    2. `emergency_withdraw_001` — execution tx `0xcaa0af2c0799d405cdcf713d5cd2f17d9f5d027578bb9789a1f827b75ff0745f` (nonce=30)
    3. `2023-11-01-001` — execution tx `0x21fc3fbc253eae804d0f5f2c19a907fd430231f1acd58725de5c66b049c4f839` (nonce=29)
    4. `2023-11-01-001` — execution tx `0xd725285ff0857ce63b70f975ff805862ae7260a40d2fd672f30991ab26df035e` (nonce=31)
    5. `12345` (lst_expansion STAKE_LST) — execution tx `0xc4b0a980d4477d2962fd5bda66e480214f55a161b7f2354100b197a1bd9479f5` (nonce=28)
*   **LangChain Bridge:** `langchain_keeperhub.py` implemented as a reusable `BaseTool`; wired into `agents/patriarch.py`'s `consult_sim_oracle` node as a first-class LangGraph step.

---

## 5. KeeperHub — "Builder Feedback" ($500)

*   **Feedback Document:** [docs/KEEPERHUB_FEEDBACK.md](docs/KEEPERHUB_FEEDBACK.md)
*   **Actionable items:** 3 friction points, 1 documentation gap.
