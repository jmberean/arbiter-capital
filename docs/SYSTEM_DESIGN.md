# System Design Specification: Autonomous Family Office (v5.0 — "Winning Edition")

**Project:** Arbiter Capital — Autonomous Multi-Agent Treasury Manager
**Target Event:** ETHGlobal Open Agents (April 24 – May 6, 2026)
**Document Status:** Frozen architecture for hackathon submission. v5.0 supersedes v4.0 with five elite features layered on top of the v4 hardening foundation.

> **v5.0 changelog (2026-04-26).** v4.0 closed the gap between docs and code (real EIP-712, true 2-of-2, hash-chained audit log, decimals discipline, Universal Router). **v5.0 layers five "winning" features on top: a custom v4 hook (`ArbiterThrottleHook`), 0G as the LLM memory substrate (not just an audit log), KeeperHub as a consensus-time simulation oracle via MCP, a Byzantine Watchdog adversary process, and Soulbound Decision Receipts with live audience verification via QR.** These are the artifacts that move the project from "well-engineered submission" to "grand-prize candidate."

---

## 0. Executive Summary

Arbiter Capital is an autonomous, multi-agent DeFi treasury manager — an **Agent Town with four personas** — that any third party can cryptographically replay. Two cognitively isolated AI personas (the **Yield Quant** and the **Risk Patriarch**) run as independent OS processes and communicate over Gensyn AXL's serverless, encrypted P2P mesh — **no centralized message broker, no shared database on the demo path** (Gensyn AXL is the only inter-process transport). They are joined by two more personas: the **Sim-Oracle Auditor** (KeeperHub MCP, providing fork-simulation as a consensus signal) and the **Byzantine Adversary** (a scripted attacker that publishes corrupt proposals during the demo to prove the system rejects them). All four communicate exclusively over AXL.

Authorization happens against a 2-of-2 Sepolia Safe through threshold ECDSA. A non-LLM Python firewall sits at the chain boundary. Every input, every LLM context, every signature, every receipt is hash-chained to **0G as the canonical AI memory substrate** — not merely as an audit log, but as the data layer that makes AI decisions cryptographically reproducible. Trades route through our own `ArbiterThrottleHook` deployed on Sepolia v4. Every settled decision mints a Soulbound Decision Receipt to the Safe; a QR on the recording links to a public verifier page so judges (watching asynchronously) can pause the video and verify the entire chain on their own machine in seconds.

**The thesis aligns directly with the hackathon theme — "AI agents that live onchain":** institutional capital does not delegate to a single LLM. We replace that single LLM with cognitive isolation across four AXL-bound personas, cryptographic accountability via per-agent EIP-712 signatures, a deterministic last-mile firewall, reproducible AI memory on 0G, and adversarial resilience demonstrated on tape.

---

## 1. Problem Statement & Solution Thesis

### 1.1 Problem
DeFi yield management requires constant monitoring, multi-asset rotation, and high-frequency execution. AI agents can compute optimal routes, but institutional capital will not trust:
* A black-box single-LLM policy that can hallucinate a $50M trade.
* An EOA-controlled treasury with no segregation of duties.
* An audit log written by the same process that produced the decision.
* Off-chain "logs" that cannot be cryptographically reproduced.
* A demo that cannot be verified by anyone outside the demo team.

### 1.2 Solution Thesis (seven invariants)
1. **Cognitive isolation** — no single process holds both yield and risk authority.
2. **Cryptographic accountability** — identity = public key; every "agreement" is an EIP-712-signed artifact.
3. **Deterministic last-mile** — non-LLM firewall whose constraints are source-controlled.
4. **Reproducible AI memory** — full LLM context (system prompt, messages, model id, temperature, schema hash, response) lives on 0G; any third party can replay the call.
5. **Adversarial resilience on camera** — the Byzantine Watchdog publishes attacks during the demo; the system rejects them visibly.
6. **Public verifiability** — Soulbound receipts + QR-served verifier page lets judges verify the chain at their own pace.
7. **Decentralized transport, no shared broker** — inter-process communication runs exclusively over Gensyn AXL on the demo path. The SQLite mock exists only for offline solo development; if a daemon detects `AXL_NODE_URL` is unset at boot during the recording, it fails closed (refuses to start). This invariant is what earns the Gensyn bounty's hard requirement.

If any of these is violated by an implementation choice, that choice is wrong.

---

## 2. Bounty Surface — Depth-Tier Analysis (v5.1, aligned with `docs/HACKATHON_DETAILS.md`)

Each bounty is rated by **depth tier** (T1 = surface use, T3 = bounty-defining integration). v5.1 targets **T3 on every bounty** AND complies with each bounty's hard requirements. Total addressable prize pool is **$50,000+**, of which $30,000 is sponsor-allocated (matrix below) and ~$20,000+ is the general/grand-prize pool keyed to the hackathon theme **"AI agents that live onchain."**

| Bounty | Pool | Tier 1 / 2 / 3 distribution | Hard requirements (DQ if missed) | **Our T3 play** |
|---|---:|---|---|---|
| **Gensyn — "Best Application of AXL"** | **$5,000** | $2.5k / $1.5k / $1.0k | (a) Use AXL for inter-agent comms — **no centralized message brokers**. (b) Demonstrate cross-node communication. Suggested track: **Agent Town** (multi-agent, personalities). | **4-persona Agent Town entirely over AXL** — Yield Quant, Risk Patriarch, Sim-Oracle Auditor (KeeperHub), Byzantine Adversary. The Adversary publishes scripted attacks during the demo; defenders reject on AXL with forensic 0G receipts. SQLite mock is fail-closed during the recording — `AXL_NODE_URL` must be set or daemons refuse to boot. |
| **0G — "Bringing AI fully on-chain"** | **$15,000** | distribution TBA per `HACKATHON_DETAILS.md` | None published. Theme: large-scale AI workloads on a decentralized AI L1. | **0G as the canonical LLM memory substrate.** Full `LLMContext` artifacts (system prompt, messages, model_id, temperature, schema hash, parsed-response hash) for *every* agent LLM call, hash-chained on 0G. `scripts/replay_decision.py` re-issues any past LLM call from 0G storage and verifies a deterministic `parsed_hash` match. This is the AI-workload-on-0G use case in literal form. |
| **KeeperHub — "Best Use of KeeperHub"** | **$4,500** | $2.5k / $1.5k / **$0.5k** (3rd is $500 — corrected) | Two focus areas, hit either or both: **(F1)** real problem via MCP/CLI, **(F2)** bridges/plugins for payment rails or **agent frameworks (LangChain, ElizaOS, …)**. | **We hit BOTH focus areas.** F1: KeeperHub MCP as a *consensus participant* via `simulate_safe_tx` (pre-execution sim oracle the Patriarch calls during eval) — not just a courier. F2: ship `langchain_keeperhub.py` — a reusable `langchain_core.tools.BaseTool` wrapper that any LangGraph project can drop in. Actively shipping a public LangChain bridge. |
| **KeeperHub — "Builder Feedback"** | **$500** | $250 × up to 2 teams | Specific, actionable feedback on UX friction, reproducible bugs, or doc gaps encountered using KeeperHub during the event. | **Ship `docs/KEEPERHUB_FEEDBACK.md`** documenting every UX friction we encountered (dated, with reproduction steps, screenshots, logs). Filed Day 9. Cheapest $250 in the pool. |
| **Uniswap Foundation — v4 / Unichain** | **$5,000** | distribution TBA | Theme: protocol innovation around v4 / Unichain. | **Deploy our own `ArbiterThrottleHook` on Sepolia.** TWAP-window throttle on Arbiter-originated swaps for anti-self-MEV — institutional-grade rationale, not toy hook. Verified contract on Etherscan, ≥1 swap routed through it on the demo path. |
| **General / Grand-Prize Pool** | **~$20,000+** | per-track jury allocation | Theme: **"AI agents that live onchain."** Beyond chatbots: autonomous execution + agent-to-agent negotiation + Ethereum-plugged infra. | The whole project IS this theme: 4 onchain-bound agents, signed negotiation, autonomous Safe execution, no human in the loop, all artifacts cryptographically reproducible. |

This depth matrix is the single most important strategic artifact in the document. Every implementation choice in `TECHNICAL_ROADMAP.md` traces back to a T3 cell here.

### 2.5 Bounty Hard-Requirement Compliance Audit

Each bounty hard requirement is mapped to the file/code path that satisfies it. The CI gate `scripts/check_bounty_compliance.py` (Day 9) re-runs this audit and refuses to ship if any row fails.

| Requirement | Source | Satisfied by | CI assertion |
|---|---|---|---|
| AXL is the *only* inter-process transport on demo path | Gensyn HR(a) | `core/network.py` boot check: if `os.getenv("DEMO_MODE")=="1"` and `AXL_NODE_URL` unset → `sys.exit(1)`. Demo runner sets both. | `assert axl_node.use_live_axl is True` in every daemon boot log |
| Cross-node communication demonstrated | Gensyn HR(b) | All 4 personas bind to *distinct* AXL node IDs; the recording shows `monitor_network.py` rendering messages whose `sender` field varies across the 4 nodes | `assert distinct_senders >= 4` in monitor's last 60s window |
| KeeperHub MCP used to solve a real problem | KeeperHub F1 | `execution/keeper_hub.py::simulate_safe_tx` is invoked by Patriarch during eval; if revert → auto-reject `SIM_REVERT` | `assert sim_oracle_invocations >= 3` per recording |
| KeeperHub bridge for a known agent framework | KeeperHub F2 | `langchain_keeperhub.py` exports `KeeperHubExecuteTool`, `KeeperHubSimulateTool` as `langchain_core.tools.BaseTool` subclasses, importable by any LangGraph project | `assert isinstance(KeeperHubExecuteTool(), BaseTool)` |
| Builder feedback document submitted | KeeperHub Builder Feedback | `docs/KEEPERHUB_FEEDBACK.md` exists, ≥3 entries with date/repro/expected/actual | file size ≥4 KB, ≥3 H2 sections |
| Custom v4 hook deployed and used | Uniswap T3 | `ARBITER_THROTTLE_HOOK` on Sepolia (verified); ≥1 swap on demo path includes it in PoolKey | check Etherscan API for verified-source flag, ≥1 swap event |
| 0G holds all LLM contexts | 0G T3 | `memory/llm_context_writer.py::capture_and_persist` writes pre-LLM-response | `assert llm_context_receipts >= 6` on demo recording |
| Receipts hash-chained on 0G | 0G T3 | `memory/audit_chain.py::AuditChainHead`; every `_write_to_0g` reads/advances head | `verify_audit.py --walk-from-head` returns success |

---

## 3. Process Topology

### 3.1 Five-process model

```
                ┌────────────────────────────────────────────────────────────┐
                │                Gensyn AXL Mesh (P2P)                       │
                │  Topics: MARKET_DATA · MARKET_SNAPSHOTS · PROPOSALS ·       │
                │          PROPOSAL_EVALUATIONS · CONSENSUS_SIGNATURES ·      │
                │          FIREWALL_CLEARED · SIM_ORACLE_REQUESTS/RESULTS ·   │
                │          EXECUTION_SUCCESS · EXECUTION_FAILURE ·            │
                │          AGENT_HEARTBEAT · AUDIT_CHAIN ·                    │
                │          ATTACK_REJECTED  (watchdog evidence stream)        │
                └────────────────────────────────────────────────────────────┘
                ▲              ▲              ▲              ▲              ▲
                │              │              │              │              │
        ┌───────┴──────┐ ┌─────┴──────┐ ┌─────┴──────────┐ ┌─┴─────────┐ ┌──┴──────────┐
        │ P1: Quant    │ │ P2: Patri- │ │ P3: Execution  │ │ P4: Sim   │ │ P5: Byzant- │
        │ (Node A)     │ │ arch (B)   │ │ Node (P3)      │ │ Oracle    │ │ ine Watchdog│
        │ LangGraph    │ │ LangGraph  │ │ Pure Python    │ │ KeeperHub │ │ (DEMO ONLY) │
        │ Math + LLM   │ │ Recompute  │ │ Sig verify     │ │ MCP server│ │ Adversarial │
        │ Quant signs  │ │ + LLM eval │ │ + Threshold    │ │ simulate_ │ │ messages    │
        │              │ │ + sim call │ │ Dedupe + 0G    │ │ safe_tx() │ │             │
        └──────────────┘ └────────────┘ └──────────────┬─┘ └───────────┘ └─────────────┘
                                                        │
                                          ┌─────────────┴───────────────┐
                                          │ Safe (Sepolia, 2-of-2)      │
                                          │   ↓ enableModule(KeeperHub) │
                                          │   ↓ KeeperHub.execTxFromMod │
                                          │   ↓ Universal Router        │
                                          │   ↓ V4_SWAP w/ Permit2      │
                                          │   ↓ PoolManager + Arbiter-  │
                                          │     ThrottleHook            │
                                          └─────────────────────────────┘

           ┌──────────────────────────────────────────────────────────┐
           │ 0G Layer 1 (Canonical AI Memory + Audit Chain)           │
           │   LLMContext (full)        → MarketSnapshot               │
           │   → DecisionReceipt        → NegotiationTranscript        │
           │   → ExecutionReceipt       → AttackRejected (forensic)    │
           │   All hash-chained via prev_0g_tx_hash                    │
           └──────────────────────────────────────────────────────────┘
           ┌──────────────────────────────────────────────────────────┐
           │ ChromaDB (local Retrieval Layer)                         │
           │   Embeds rationale + LLM context + 0G tx hash            │
           └──────────────────────────────────────────────────────────┘
           ┌──────────────────────────────────────────────────────────┐
           │ ArbiterReceipt (ERC-721 SBT) on Sepolia                  │
           │   tokenId = keccak256(receipt_hash)                      │
           │   tokenURI = 0g://<receipt_tx_hash>                      │
           │   minted to Safe on every EXECUTION_SUCCESS              │
           └──────────────────────────────────────────────────────────┘
```

### 3.2 Process responsibilities

| Process | Cognition | Holds Keys | Reads Chain | Writes Chain | AXL Node ID | Required for demo? |
|---|---|:-:|:-:|:-:|---|:-:|
| Quant (P1) | LangGraph + GPT-4o + math tools | `QUANT_KEY` (Safe owner) | YES (price feeds, pool state) | NO | `Quant_Node_A` | YES |
| Patriarch (P2) | LangGraph + GPT-4o + sim consumer | `PATRIARCH_KEY` (Safe owner) | YES (via Sim Oracle) | NO | `Patriarch_Node_B` | YES |
| Execution (P3) | None (pure Python) | `EXECUTOR_KEY` (gas only) | YES | YES (Safe + 0G + SBT mint) | `Execution_Node_P3` | YES |
| Sim Oracle (P4) | None (KeeperHub MCP) | `KEEPERHUB_ATTESTOR_KEY` (advisory) | YES (simulate via fork) | NO | `KeeperHub_Sim_P4` | YES |
| Byzantine Watchdog (P5) | Scripted attacker | `ATTACKER_KEY` (NOT a Safe owner) | NO | NO (writes only to AXL) | `Adversary_Node_Z` | YES (demo recording only) |

**Five distinct AXL node IDs over the wire — this is the literal cross-node communication evidence Gensyn judges look for.** The monitor's "Sender" column visibly cycles through all five during the recording.

**Key separation principle (unchanged):** the Executor key only pays gas; it has no Safe owner authority. Even if compromised, it cannot move treasury funds without a valid 2-of-2 Quant+Patriarch signature.

**Transport invariant:** every daemon's `__init__` asserts `axl_node.use_live_axl is True` when `DEMO_MODE=1`. The SQLite mock is for offline solo dev only and fails closed during the recording. See `core/network.py::_assert_demo_transport`.

### 3.3 Canonical AXL topic catalog

| Topic | Producer | Consumer | Idempotency Key | Wire Schema |
|---|---|---|---|---|
| `MARKET_DATA` | MarketGod / oracle | Quant | `snapshot_id` | `MarketSnapshot` |
| `MARKET_SNAPSHOTS` | Quant (re-publish) | Patriarch | `snapshot_hash` | `MarketSnapshot` |
| `PROPOSALS` | Quant | Patriarch, Monitor | `proposal_id` | `Proposal` (with `quant_signature`) |
| `PROPOSAL_EVALUATIONS` | Patriarch | Quant, Execution, Monitor | `(proposal_id, iteration)` | `ProposalEvaluation` |
| `SIM_ORACLE_REQUEST` | Patriarch | Sim Oracle | `(proposal_id, iteration)` | `SimulationRequest` |
| `SIM_ORACLE_RESULT` | Sim Oracle | Patriarch | request hash | `SimulationResult` |
| `CONSENSUS_SIGNATURES` | Quant + Patriarch | Execution, Monitor | `(proposal_id, signer_id)` | `ConsensusMessage` |
| `FIREWALL_CLEARED` | Patriarch | Execution | `proposal_id` | `Proposal` (cleared flag) |
| `EXECUTION_SUCCESS` | Execution | All | `tx_hash` | `ExecutionReceipt` |
| `EXECUTION_FAILURE` | Execution | All | `(proposal_id, attempt)` | `ExecutionFailure` |
| `AGENT_HEARTBEAT` | All daemons | All | `(node_id, ts)` | `Heartbeat` |
| `AUDIT_CHAIN` | Execution | Verifier, Monitor | `this_0g_hash` | `AuditLink` |
| `ATTACK_REJECTED` | Quant / Patriarch / Exec | Monitor | `(attack_id, defender)` | `AttackRejection` (forensic record of watchdog rejection) |

Every payload is a Pydantic `BaseModel`, JSON-serialized with `sort_keys=True`, and wrapped in an envelope with `producer_node_id`, `producer_signature`, and `producer_pubkey`. Receivers verify the envelope before processing.

---

## 4. Data Models & Cryptographic Identifiers

### 4.1 Proposal (extended)

```python
class Proposal(BaseModel):
    # Identity
    proposal_id: str
    parent_proposal_id: Optional[str]
    iteration: int

    # Trade specification
    target_protocol: Literal["Uniswap_V4", "Lido", "Pendle"]
    v4_hook_required: Optional[Literal["Volatility_Oracle", "Dynamic_Fee", "ArbiterThrottle", "None"]]
    action: ActionType
    asset_in: str
    asset_out: Optional[str]
    asset_in_decimals: int
    asset_out_decimals: Optional[int]
    amount_in_units: str                 # base-units string
    min_amount_out_units: Optional[str]
    deadline_unix: int

    # Quantitative attestation (from deterministic math tool)
    projected_apy_bps: int
    risk_score_bps: int
    quant_analysis_hash: str

    # Market input snapshot (so Patriarch can recompute)
    market_snapshot_hash: str

    # LLM provenance (so anyone can replay)
    llm_context_hash: str                # keccak of LLMContext JSON
    llm_context_0g_tx: Optional[str]     # 0G tx where LLMContext was stored

    # Negotiation
    rationale: str
    consensus_status: ConsensusStatus

    # Cryptographic envelope
    proposal_hash: str                   # EIP-712 typed-data hash
    safe_tx_hash: Optional[str]
    quant_signature: Optional[str]       # 130-hex (sig_proposal || sig_safe)
    patriarch_signature: Optional[str]
    safe_nonce: Optional[int]
    chain_id: int
```

### 4.2 LLMContext (NEW in v5 — the artifact that earns the 0G bounty)

```python
class LLMContext(BaseModel):
    """
    Canonical record of every LLM call. Stored on 0G alongside the proposal.
    Anyone can re-issue the call against the same (model_id, system_prompt, messages,
    temperature, structured_output_schema_hash) and inspect the response.
    """
    schema_version: int = 1
    call_id: str                          # uuid4 hex
    invoking_agent: Literal["Quant_Node_A", "Patriarch_Node_B"]
    invoked_at: float
    proposal_id: str
    iteration: int

    model_id: str                         # e.g. "openai/gpt-4o-2026-03"
    temperature: float
    seed: Optional[int]
    structured_output_schema_hash: str    # keccak of the Pydantic JSON schema
    structured_output_schema_name: str

    system_prompt: str
    messages: list[dict]                  # full message array, untruncated
    response_raw: str                     # raw LLM string before Pydantic parse
    response_parsed_hash: str             # keccak of the parsed object
    tools_invoked: list[str]              # names of LangGraph tools called

    context_hash: str                     # keccak(canonical(self minus context_hash))
```

Every LLM call in the system writes one `LLMContext` to 0G before the proposal is published.

### 4.3 ConsensusBundle (NEW — single signed object instead of two parallel sigs)

```python
class ConsensusBundle(BaseModel):
    """
    Both hashes (proposal_hash + safe_tx_hash) bundled and signed once per agent.
    Reduces wire footprint and gives Safe a clean signatures blob.
    """
    proposal_id: str
    iteration: int
    proposal_hash: str
    safe_tx_hash: str
    bundle_hash: str                      # keccak(proposal_hash || safe_tx_hash)
    quant_signer: str                     # Quant's checksummed address
    quant_signature_bundle: str           # signs bundle_hash
    quant_signature_safe: str             # signs safe_tx_hash (Safe needs this raw)
    patriarch_signer: Optional[str]
    patriarch_signature_bundle: Optional[str]
    patriarch_signature_safe: Optional[str]
```

The Safe ultimately needs `signature_safe` for `execTransaction`. The `signature_bundle` is what the verifier uses to prove "both agents agreed to the *full* proposal, not just the executable payload."

### 4.4 SimulationRequest / SimulationResult (NEW — KeeperHub as oracle)

```python
class SimulationRequest(BaseModel):
    request_id: str
    proposal_id: str
    iteration: int
    safe_address: str
    to: str
    value: int
    data: str                             # hex
    operation: int
    requested_by: Literal["Patriarch_Node_B"]
    timestamp: float

class SimulationResult(BaseModel):
    request_id: str
    proposal_id: str
    success: bool
    gas_used: int
    return_data: str
    revert_reason: Optional[str]
    fork_block: int                       # block number forked at
    simulator_signature: str              # KeeperHub signs the result envelope
    timestamp: float
```

KeeperHub signs every simulation result. The Patriarch verifies the signature (KeeperHub's pubkey is in `OWNER_REGISTRY` as a non-Safe-owner *attestor*) and rejects unsigned simulations.

### 4.5 AttackRejection (NEW — forensic record from the Byzantine Watchdog)

```python
class AttackRejection(BaseModel):
    attack_id: str
    attacker_node_id: str
    attack_kind: Literal[
        "INVALID_SIGNATURE", "REPLAY_NONCE", "MATH_FORGE",
        "WHITELIST_BYPASS", "FAKE_SIM_RESULT", "WRONG_DOMAIN",
    ]
    detected_at: float
    detected_by: Literal["Quant_Node_A", "Patriarch_Node_B", "Execution_Node_P3"]
    evidence: dict                        # the rejected payload (truncated)
    rejection_reason: str
    publish_to_0g: bool = True            # forensic records go on-chain too
```

Every watchdog attack and its rejection are written to 0G. Future operators can audit how the system *would* respond to a corrupted node.

### 4.6 Receipt taxonomy (extended)

```
0G receipts (all hash-chained via prev_0g_tx_hash):
├─ LLMContext             — every LLM call
├─ MarketSnapshot         — every input snapshot
├─ NegotiationTranscript  — per iteration
├─ DecisionReceipt        — at consensus (pre-execution)
├─ ExecutionReceipt       — post on-chain confirmation
├─ RejectionReceipt       — proposal expired or firewall-rejected
└─ AttackRejection        — Byzantine Watchdog evidence
```

---

## 5. Math-First Cognition (Quant)

### 5.1 Why math-first
The LLM never sees a price. It sees the *output* of a deterministic tool. This is the primary defense against hallucination, and `quant_analysis_hash` is the contract that enforces it.

### 5.2 Deterministic Tool Surface

| Tool | Inputs | Outputs | Live Source | Demo Source |
|---|---|---|---|---|
| `compute_volatility(asset, window)` | asset, window_hours | realized_vol, GARCH(1,1) 48h forecast | Subgraph swap events | `market_god` |
| `compute_yield_spread(strategy)` | strategy enum | apy_bps, tvl_usd, safety_score | Pendle/Lido APIs | `market_god` |
| `compute_gas_breakeven(action, amount)` | action, amount | breakeven_amount_usd, expected_gas_usd | gas oracle | scenario gwei |
| `compute_kelly_size(edge, var, balance)` | edge_bps, variance, treasury_units | optimal_size_units, capped_size_units | — | — |
| `simulate_swap(pool_key, amount_in)` | pool_key, amount_in_units | expected_amount_out_units, price_impact_bps | v4 quoter | analytical |
| `recall_similar(query, n)` | query, n | list of past `DecisionReceipt` (pulled from 0G, integrity-verified) | 0G + ChromaDB | local |

### 5.3 Quant LangGraph (with v5 LLM-context capture)

```
[ingest_data] → [run_math_tools] → [recall_memory] → [draft_proposal_llm]
                                                            │
                                                  [capture_llm_context] ── 0G write
                                                            │
                                                      [self_audit]
                                                            │
                                                 [build_safe_tx_hash]
                                                            │
                                                     [sign_bundle] → END
```

* `capture_llm_context` writes the `LLMContext` to 0G immediately after every LLM call. The `llm_context_0g_tx` tx hash is then attached to the Proposal so the Patriarch (and the public verifier) can pull and replay.
* `sign_bundle` produces a `ConsensusBundle` with `quant_signature_bundle` (over `bundle_hash`) and `quant_signature_safe` (over `safe_tx_hash`).

### 5.4 Sizing & Risk Math
* **Volatility:** GARCH(1,1) on hourly returns from on-chain swap events.
* **Kelly sizing (capped):** `f* = (μ − r)/σ²`, clamped to `[0, MAX_FRACTION_OF_TREASURY = 0.25]`.
* **Gas profitability:** rejected pre-LLM if `expected_revenue_per_week < 1.5 × expected_gas_usd`.
* **Decimals discipline:** `compute_kelly_size` returns `optimal_size_units: str` in base units of `asset_in`. End-to-end base-units strings.

---

## 6. Risk Evaluation (Patriarch)

### 6.1 Constrained LLM output
Patriarch's LLM emits a `ProposalEvaluation` only — never a full `Proposal`. The numeric fields cannot be rewritten by the LLM.

### 6.2 Three layers of risk gating
1. **Pre-LLM deterministic gate** (whitelist, max value, deadline, drawdown ledger, hook permission bits).
2. **LLM evaluation** with `with_structured_output(ProposalEvaluation)`.
3. **Post-LLM deterministic override** (math recompute, simulation oracle, signer verification on incoming `quant_signature`).

### 6.3 Patriarch invokes the Simulation Oracle (v5 elite feature)

After the LLM evaluation tentatively returns `ACCEPTED`, the Patriarch publishes a `SimulationRequest` on AXL and waits up to 8s for a signed `SimulationResult` from KeeperHub. If the simulation reverts, the proposal is auto-rejected with `OUTSIDE_MANDATE`. The simulation result is included in the `NegotiationTranscript`.

This makes KeeperHub a **third Byzantine voice in consensus**, not just a delivery courier — a key differentiator for the KeeperHub bounty.

### 6.4 Patriarch independently re-runs the math
The Patriarch fetches `MarketSnapshot` by `market_snapshot_hash`, re-executes the same math tool, and rejects on `MATH_MISMATCH` if `quant_analysis_hash` diverges.

---

## 7. Negotiation Protocol & Convergence

### 7.1 State machine
```
                       ┌── reject (iter < 3) ──┐
                       │                       ▼
[draft] → [propose] → [evaluate] → reject (iter ≥ 3) → [EXPIRED] → 0G RejectionReceipt
                          │
                          └── accept ──→ [sim_oracle] ──→ accept ──→ [firewall] ──→ [execute]
                                            │
                                            └── revert ──→ [REJECTED:OUTSIDE_MANDATE]
```

### 7.2 Convergence guarantees
* Math invariance — Quant cannot invent better numbers between iterations; only `amount_in_units` (within Kelly) and the rationale narrative may change.
* Iteration cap = 3.
* Rejection-reason taxonomy — fixed enum; deterministic Quant revision logic per reason.
* Heartbeat-driven liveness with 30s patriarch-silence timeout.

---

## 8. Cryptographic Consensus

### 8.1 Two distinct hashes, one bundle
* **`proposal_hash`** — EIP-712 hash of the full `Proposal` artifact (the agreement on *what was decided*).
* **`safe_tx_hash`** — EIP-712 hash per Safe's `domainSeparator` (what's *executed* on-chain).
* **`bundle_hash` = keccak(proposal_hash ‖ safe_tx_hash)** — the canonical agent-attestation digest.

Each agent signs `bundle_hash` (for audit) **and** `safe_tx_hash` (for Safe's `execTransaction`). Two signatures per agent, four signatures total in a 2-of-2.

### 8.2 EIP-712 domain (Proposal)
```
domain = {
    name:    "ArbiterCapital",
    version: "1",
    chainId: 11155111,
    verifyingContract: SAFE_ADDRESS,
}
```

Tying the domain to the Safe address means a stolen `Proposal` cannot be replayed against any other Safe.

### 8.3 Signing flow
1. Quant: builds Proposal → computes `proposal_hash` → reads `safe_nonce` → builds Safe tx → computes `safe_tx_hash` → builds bundle → signs both → publishes `Proposal` and a partial `ConsensusBundle`.
2. Patriarch: verifies Quant's bundle signature → recomputes math → invokes Sim Oracle → on accept, signs both bundle + safe_tx → publishes complete `ConsensusBundle`.
3. Execution Node: verifies *both* signatures recover to addresses in `OWNER_REGISTRY`; verifies `safe_nonce` equals current Safe nonce on chain; verifies dedupe ledger has no entry for `(safe_address, safe_nonce)`; assembles Safe-format signatures (sorted by address ascending); calls KeeperHub.

### 8.4 True 2-of-2 with on-chain verification
The Safe contract itself verifies threshold = 2 at `execTransaction`. The off-chain verification in the Execution Node is a fast-fail before paying gas; the on-chain check is the real authority.

### 8.5 Why ECDSA, not BLS / Schnorr / threshold-Schnorr
Safe's `execTransaction` verifies ECDSA. Anything else means a custom verifier contract — out of scope for the hackathon.

---

## 9. Deterministic Policy Firewall

```python
WHITELISTED_ASSETS = {"WETH", "USDC", "stETH", "WBTC", "PT-USDC"}
WHITELISTED_PROTOCOLS = {"Uniswap_V4", "Lido", "Pendle"}
ALLOWED_HOOKS = {V4_HOOK_VOL_ORACLE, V4_HOOK_DYNAMIC_FEE, ARBITER_THROTTLE_HOOK, ZERO_ADDRESS}
MAX_TRANSACTION_VALUE_USD = 50_000
MAX_DAILY_DRAWDOWN_BPS = 500
MAX_PER_ASSET_ALLOCATION_BPS = 4_000
MAX_GAS_PRICE_GWEI = 500
MIN_PROPOSAL_DEADLINE_SECONDS = 60
```

Every clearance produces a `FirewallDecision` written to AXL and 0G. **Hook addresses are validated at the bit level**: the bottom 14 bits of a v4 hook address encode the hook's permissions. The firewall asserts the exact permission bit set required for each hook role (e.g., `BEFORE_SWAP_FLAG | AFTER_SWAP_FLAG` for the ArbiterThrottleHook). A hook whose address bits don't match is rejected — defense against spoofed hook addresses.

---

## 10. DeFi Execution Layer

### 10.1 Safe + KeeperHub topology
* **Safe (Sepolia)** — owners `[QUANT_ADDR, PATRIARCH_ADDR]`, threshold 2.
* **KeeperHub** — Safe **Module** via `enableModule(KEEPERHUB_ADDR)`. Calls `execTransactionFromModule(to, value, data, op)` after off-chain verifying the bundled 2-of-2 signatures. Also runs a separate MCP daemon offering `simulate_safe_tx`.
* **Executor EOA** — pays gas only.

### 10.2 v4 execution path: Universal Router + Permit2

```
KeeperHub
  → Safe.execTransactionFromModule(to=UR, ..., data=URExecute)
      → UniversalRouter.execute(commands, inputs, deadline)
          → PERMIT2_PERMIT command (if needed)
          → V4_SWAP command with PoolKey + SwapParams + hookData
              → PoolManager.unlock(...) [internal]
                  → PoolManager.swap(...)
                      → ArbiterThrottleHook.beforeSwap(...) ✱ v5
                      → ArbiterThrottleHook.afterSwap(...)  ✱ v5
```

### 10.3 ArbiterThrottleHook (v5 elite feature — our own deployed v4 hook)

**Purpose:** prevent self-MEV by throttling consecutive Arbiter-originated swaps within a TWAP window.

**Solidity sketch (`hooks/ArbiterThrottleHook.sol`):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {BaseHook} from "@uniswap/v4-periphery/contracts/utils/BaseHook.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "@uniswap/v4-core/src/types/BeforeSwapDelta.sol";

contract ArbiterThrottleHook is BaseHook {
    address public immutable arbiterSafe;        // the Arbiter Capital Safe
    uint256 public immutable minIntervalSeconds; // e.g. 60s between Arbiter swaps
    uint256 public immutable maxNotionalPerWindow; // USD-denominated, oracle-fed
    mapping(bytes32 => uint256) public lastSwapAt;          // poolId => last swap ts
    mapping(bytes32 => uint256) public windowNotionalUsed;  // poolId => running notional

    constructor(IPoolManager m, address safe, uint256 interval, uint256 cap)
        BaseHook(m) { arbiterSafe = safe; minIntervalSeconds = interval; maxNotionalPerWindow = cap; }

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize:false, afterInitialize:false,
            beforeAddLiquidity:false, afterAddLiquidity:false,
            beforeRemoveLiquidity:false, afterRemoveLiquidity:false,
            beforeSwap:true, afterSwap:true,
            beforeDonate:false, afterDonate:false,
            beforeSwapReturnDelta:false, afterSwapReturnDelta:false,
            afterAddLiquidityReturnDelta:false, afterRemoveLiquidityReturnDelta:false
        });
    }

    function _beforeSwap(address sender, PoolKey calldata key, IPoolManager.SwapParams calldata p, bytes calldata)
        internal override returns (bytes4, BeforeSwapDelta, uint24)
    {
        if (sender == arbiterSafe) {
            bytes32 id = keccak256(abi.encode(key));
            require(block.timestamp >= lastSwapAt[id] + minIntervalSeconds, "ArbiterThrottle: cooldown");
            // TWAP-window notional check happens in afterSwap (we know the actual amount)
        }
        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function _afterSwap(address sender, PoolKey calldata key, IPoolManager.SwapParams calldata p,
        BalanceDelta delta, bytes calldata) internal override returns (bytes4, int128) {
        if (sender == arbiterSafe) {
            bytes32 id = keccak256(abi.encode(key));
            lastSwapAt[id] = block.timestamp;
            // (Notional accounting omitted for brevity)
        }
        return (BaseHook.afterSwap.selector, 0);
    }
}
```

**Address mining:** v4 hooks encode permissions in the bottom 14 bits of their address. We use `HookMiner` (Uniswap pattern) to mine a CREATE2 salt yielding an address with `BEFORE_SWAP_FLAG | AFTER_SWAP_FLAG` set. Deploy via Foundry on Sepolia. Pin as `ARBITER_THROTTLE_HOOK` in `.env`.

**Why this wins Uniswap:** judges have publicly stated that "deploy your own hook" is the gold-standard for the v4 track. ArbiterThrottle is also institutionally meaningful (anti-self-MEV), not a toy hook.

### 10.4 Permit2 integration
Once-per-asset Permit2 approvals batched into the first UR `execute`. Subsequent swaps use Permit2's allowance map. `MAX_UINT160` allowance is rejected by the firewall — we use bounded approvals with 24h expiry.

### 10.5 Slippage & deadlines
* `min_amount_out_units = simulate_swap.quoter_out × (1 − PROPOSAL_SLIPPAGE_BPS/10000)`. Default `PROPOSAL_SLIPPAGE_BPS = 30`.
* `deadline_unix = now() + 300s`.
* Both signed inside the Proposal — cannot be silently changed between sign-time and execute-time.

---

## 11. 0G as the LLM Memory Substrate (v5 elite feature — depth on the $15k bounty)

### 11.1 Three classes of writes
| Class | Frequency | Size | Why on 0G |
|---|---|---|---|
| **LLMContext** | Per LLM call (~6/decision) | 5–20 KB | Reproducibility of AI decisions; the canonical 0G use case |
| **Decision artifacts** | Per consensus | 2–10 KB | Audit trail |
| **Forensics** | Per attack rejection | 0.5–2 KB | Post-incident analysis |

### 11.2 Hash-chained log
Every receipt carries `prev_0g_tx_hash`, forming an append-only Merkle-style chain. Tampering with `Receipt_k` requires regenerating every subsequent on-chain entry — impossible after confirmation.

### 11.3 ChromaDB role
ChromaDB stores only embeddings + 0G tx pointers. No content is canonical in ChromaDB. Agents always re-pull from 0G and verify `receipt_hash` before using it for cognition.

### 11.4 Replay tool (`replay_decision.py`)
```
$ python replay_decision.py --proposal-id prop_8f72c
[1/4] Pulling DecisionReceipt prop_8f72c from 0G ... 0xabc...
[2/4] Pulling LLMContext (Quant draft_proposal) ... 0xdef...
[3/4] Re-issuing OpenAI call:
        model_id=gpt-4o-2026-03  temperature=0.2  seed=42
        system_prompt_hash=0x...
        messages: 4 entries (verified hash match)
[4/4] Comparing structured response ...
        original_response_parsed_hash=0x111...
        replay_response_parsed_hash  =0x111...   ✓ DETERMINISTIC MATCH
```

This script is the single most important demo asset for the 0G bounty. Run it on stage.

### 11.5 Embedding pipeline isolation
Default OpenAI `text-embedding-3-small`. With `EMBEDDINGS_LOCAL=1`, switches to a local `bge-small-en` model — required for offline demo recording in case OpenAI rate-limits during the recording.

---

## 12. KeeperHub Simulation Oracle (v5 elite feature — depth on the KeeperHub bounty)

### 12.1 Role expansion
KeeperHub is no longer just the Safe Module that broadcasts. It runs a separate MCP server exposing tools that participate in the agent consensus:

| MCP Tool | Caller | Purpose |
|---|---|---|
| `simulate_safe_tx(to, value, data, op)` | Patriarch (eval) | Fork-simulates the Safe tx; returns success/revert + return data |
| `get_safe_nonce()` | Quant (signing) | Authoritative nonce read |
| `verify_module_enabled()` | Execution Node (boot) | Health check |
| `execute_safe_transaction(to, value, data, signatures)` | Execution Node | Final on-chain submit |

### 12.2 Simulation semantics
KeeperHub forks Sepolia at `latest`, applies the Safe's `execTransactionFromModule` against the fork, returns:
* `success: bool`
* `gas_used: uint256`
* `return_data: bytes`
* `revert_reason: string|null`
* `fork_block: uint256`

Result is signed with KeeperHub's attestor key (registered in `OWNER_REGISTRY` as a non-Safe-owner attestor). Patriarch verifies signature before accepting.

### 12.3 Why this wins KeeperHub
KeeperHub becomes a *third Byzantine voice* — it can veto a trade by reverting the simulation. Judges have not seen MCP framed as a consensus protocol before. This is the v5 thesis: **MCP as a protocol, not an RPC.**

---

## 13. Soulbound Decision Receipt (v5 elite feature — institutional artifact)

### 13.1 ArbiterReceipt contract (ERC-721 SBT on Sepolia)
```solidity
contract ArbiterReceipt is ERC721 {
    address public immutable safeTreasury;
    address public immutable executor;          // execution node EOA — only minter
    mapping(uint256 => string) private _tokenURIs;

    constructor(address safe, address exec) ERC721("Arbiter Decision Receipt","ARDR")
    { safeTreasury = safe; executor = exec; }

    function mintReceipt(bytes32 receiptHash, string calldata zeroGUri) external returns (uint256) {
        require(msg.sender == executor, "only executor");
        uint256 id = uint256(receiptHash);
        _safeMint(safeTreasury, id);
        _tokenURIs[id] = zeroGUri;              // e.g. "0g://0xabc..."
        return id;
    }

    function tokenURI(uint256 id) public view override returns (string memory) {
        return _tokenURIs[id];
    }

    // SBT — non-transferable
    function _update(address to, uint256 id, address auth) internal override returns (address) {
        address from = _ownerOf(id);
        require(from == address(0) || to == address(0), "SBT: non-transferable");
        return super._update(to, id, auth);
    }
}
```

### 13.2 What this earns
* A tangible deployable contract judges can browse on Sepolia.
* The Safe's "owned NFTs" page shows a growing portfolio of cryptographically-signed decisions.
* Each NFT is a clickable bridge from "I see the Safe" to "I see the AI memory on 0G."

---

## 14. Byzantine Watchdog (v5 elite feature — adversarial demo)

### 14.1 Process
A 5th process, `byzantine_watchdog.py`, runs only during the demo recording. It owns `ATTACKER_KEY` (NOT a Safe owner), connects to AXL with node id `Adversary_Node_Z`, and publishes a scripted sequence of attacks:

| Attack ID | Attack Kind | Expected Defender | Expected Reaction |
|---|---|---|---|
| A1 | INVALID_SIGNATURE — fake `quant_signature` on a real Proposal | Patriarch | Discard pre-eval, publish `ATTACK_REJECTED` |
| A2 | REPLAY_NONCE — re-publish a `CONSENSUS_SIGNATURES` from an already-executed proposal | Execution Node | Dedupe ledger blocks, publish `ATTACK_REJECTED` |
| A3 | MATH_FORGE — Proposal with mutated `risk_score_bps` and stale `quant_analysis_hash` | Patriarch | `MATH_MISMATCH` reject |
| A4 | WHITELIST_BYPASS — proposal `asset_in="DOGE"` | Patriarch firewall | Pre-LLM gate, publish `ATTACK_REJECTED` |
| A5 | FAKE_SIM_RESULT — unsigned `SimulationResult` claiming success | Patriarch | Reject simulator signature, publish `ATTACK_REJECTED` |
| A6 | WRONG_DOMAIN — Proposal with `chain_id=1` (mainnet) instead of Sepolia | Patriarch | EIP-712 domain mismatch, signature won't recover to Quant |

### 14.2 Forensic record
Every rejection writes an `AttackRejection` to 0G. The verifier's chain walk shows these alongside legitimate decisions, proving the system *demonstrably* rejected attacks during the recording.

### 14.3 Why this wins Gensyn / Agent Town
"Multiple processes" without adversarial robustness is just topology. **Live, scripted Byzantine attacks rejected on camera** is what proves the architecture is real. Few hackathon teams will have the courage to let a hostile node onto the bus during their recorded demo.

---

## 15. Failure Modes, Recovery & Idempotency

### 15.1 Cursor persistence
Daemons persist `last_*_id` to `state/<process>.cursors.json` after each batch. Restarts resume from cursor — no replay from id 0.

### 15.2 Deduplication ledger
`state/executed_proposals.sqlite` keyed `(safe_address, safe_nonce)`. Execution refuses any proposal whose nonce is already settled.

### 15.3 Reorg-aware verifier
Verifier waits `MIN_CONFIRMATIONS=3` before declaring a 0G receipt confirmed.

### 15.4 RPC reconnection
Exponential backoff with jitter (250ms base, ×2, max 30s, max 8 attempts). Persistent failure surfaces as `SystemDegraded`; Execution Node enters drain-only mode.

### 15.5 Chaos test matrix (must pass before demo)

| Chaos event | Expected behavior |
|---|---|
| Kill Patriarch mid-negotiation | Quant times out at 30s, marks `EXPIRED`, writes RejectionReceipt |
| Kill Execution Node after 1 sig collected | On restart, picks up cursors, completes 2-of-2, dedupes, executes once |
| 0G RPC offline 60s | Receipts queue in `state/pending_0g.jsonl`, replayed on RPC return |
| Sepolia gas spike to 1500 gwei | Firewall (`MAX_GAS_PRICE_GWEI=500`) rejects, `EXECUTION_FAILURE` |
| MarketGod malformed payload | Quant Pydantic-rejects, emits `INGESTION_REJECTED` |
| KeeperHub MCP server crash | Patriarch sim-oracle timeout 8s ⇒ auto-reject `OUTSIDE_MANDATE` |
| All six Byzantine attacks (A1–A6) | All rejected, all forensically logged |

---

## 16. Security Threat Model

| Threat | Mitigation |
|---|---|
| Compromised Quant key | Patriarch refuses to sign; threshold=2 protects funds |
| Compromised Patriarch key | Symmetric — Quant won't propose; Patriarch alone can't move funds |
| Compromised Executor EOA | No Safe ownership; can only stop submitting (liveness, not safety) |
| MITM on AXL rewrites proposal | Each proposal carries `quant_signature`; Patriarch verifies |
| Replay of old `safe_tx_hash` | `safe_nonce` in EIP-712; old hashes stale once chain advances; dedupe ledger blocks |
| LLM hallucinates risk score | `quant_analysis_hash` enforced; Patriarch recomputes; `MATH_MISMATCH` reject |
| LLM hallucinates Safe address | `verifyingContract` in EIP-712 domain — wrong Safe ⇒ signature won't recover |
| Censorship of `EXECUTION_SUCCESS` | Verifier reads chain directly, not via AXL |
| Adversary publishes fake `CONSENSUS_SIGNATURES` | Recovers to non-registered address, ignored |
| Hook contract reverts mid-swap | UR reverts atomically; Safe tx fails; no funds moved |
| KeeperHub fakes simulation success | Patriarch verifies KeeperHub's attestor signature; unsigned ⇒ reject |
| Compromised KeeperHub key | Sim Oracle is advisory only — math + firewall remain authoritative |
| Adversary deploys spoofed hook | Hook permission bits validated bit-level by firewall |

---

## 17. Demo Storyboard — The 3-Minute Recording (Async Format)

**Format reality:** ETHGlobal Open Agents is fully asynchronous (`HACKATHON_DETAILS.md`). Judges watch the recording in solitude on their own machine, not live in a room. This is *better* for our verifier-page concept — judges can pause the video, scan the QR with their phone *or* click the on-screen URL, and verify on their own hardware. The QR is sized for both phone-camera scan and screen-grab-recognition.

**Recording mode:** OBS, 1920×1080, multi-source layout. Tabs: Monitor (full-pane left), Sepolia Etherscan (right top), 0G Explorer (right middle), Verifier page on a second device captured as picture-in-picture (right bottom — proves the QR works on a *different* machine, not just the recording machine).

| t (mm:ss) | On-screen | Voiceover |
|---|---|---|
| 0:00 | Monitor: Idle. Daemons green. | "Arbiter Capital is an autonomous family office — two AI agents, one Safe, zero black boxes." |
| 0:08 | Architecture overlay (5-process diagram). | "Quant proposes. Patriarch reviews. Execution settles. KeeperHub simulates. The Watchdog attacks." |
| 0:18 | Trigger `flash_crash_eth`. Monitor lights up MARKET_DATA → PROPOSALS. | "Volatility spikes. Quant runs GARCH, computes Kelly size, signs with EIP-712 — cryptographic identity, not a name." |
| 0:35 | Patriarch reads Proposal. KeeperHub `SIM_ORACLE_REQUEST` flashes. SimulationResult arrives signed. | "Patriarch independently re-runs the math, then asks KeeperHub to fork-simulate the Safe transaction. KeeperHub is now part of consensus." |
| 0:50 | 2-of-2 signatures collected (green). 0G LLMContext written (clickable). | "Both agents sign. The full LLM context — system prompt, model id, parsed response — goes to 0G. Anyone can replay this AI decision." |
| 1:02 | KeeperHub.execTransaction Sepolia tx confirmed. SBT mints. QR refreshes. | "Universal Router routes through our own ArbiterThrottleHook — preventing self-MEV. The Safe receives a Soulbound Decision NFT." |
| 1:18 | Picture-in-picture: a *separate* laptop scans the QR shown on the main screen and the verifier page renders `CHAIN VERIFIED ✓ N receipts` with the SAME on-chain state. | "Pause this video and scan the QR. Your machine — not ours — verifies the entire audit chain in 5 seconds. The 0G receipt hashes you see match the ones on screen." |
| 1:30 | Trigger `pendle_yield_arbitrage`. First iteration REJECTED for over-sizing. Second iteration ACCEPTED. | "Patriarch rejects size 1; Quant downsizes via deterministic revision; iteration 2 clears." |
| 1:50 | **Byzantine Watchdog fires.** Six red-flash ATTACK_REJECTED events scroll. Each shows the attack kind + defender. | "Now the Adversary publishes six attacks: forged signatures, replay nonces, hallucinated math, whitelist bypass, fake simulation, wrong chain. Every one rejected, every one forensically logged on 0G." |
| 2:20 | Trigger `protocol_hack`. SOL safety crashes. Emergency Withdraw fires fast. | "Emergency Withdraw — within the deadline window, cleared by both agents, executed in 18 seconds." |
| 2:38 | Trigger `gas_war`. Quant's breakeven turns negative. No proposal emitted. | "Gas at 850 gwei? The Quant computes a negative breakeven and refuses to trade. Cost-vs-yield reasoning, deterministic." |
| 2:52 | `replay_decision.py` runs on stage; deterministic match. | "Reproducible AI memory: re-issued the original LLM call from 0G storage. Same response hash. Verifiable cognition." |
| 3:00 | Final pane: `verify_audit.py --walk-from-head` prints `CHAIN VERIFIED` over 12 receipts. | "Twelve receipts, all hash-chained, all cryptographically reproducible. Arbiter Capital." |

**Insurance shots (pre-recorded fallback in case live recording fails):**
* `flash_crash_eth` execution from Day 9 dress rehearsal.
* Watchdog attack rejections recorded in isolation.
* `replay_decision.py` deterministic match.

---

## 18. Judge-Verifiable Proof (`audit.arbiter.capital`)

A small static site (deployable to Vercel/Netlify on Day 9) renders a live view of:
* The current head of the audit chain (read from 0G via public RPC).
* The full receipt graph, walkable.
* Per-receipt: signature recovery results, decimals-correct USD value, link to the SBT on Sepolia, link to the LLM context, link to the underlying Sepolia execution tx.

The Monitor displays a QR linking to this page. **In the async-judging context, this is the single most important UX decision in the project**: judges who finish the video and want to verify our claims do not need our cooperation, our credentials, or our test environment. They get the URL, they walk the chain in their own browser, they see `CHAIN VERIFIED` in 5 seconds. Submission link includes the URL pinned in `BOUNTY_PROOF.md`.

---

## 19. Out-of-Scope (post-hackathon v6)

* True threshold-ECDSA / FROST.
* MEV protection via Flashbots Protect on mainnet.
* DAO-governed firewall constants.
* Cross-chain treasury via LayerZero/Wormhole.
* Real-time Chainlink price oracle in firewall.
* Formal verification of firewall + ArbiterThrottleHook (Halmos / Certora).
* Patriarch ensemble (2-of-3 distinct LLM providers) for hallucination resistance.
* Slashing economics (bonded agent stakes, slash on signed-but-failed proposals).

---

## Appendix A: Repository Layout (canonical, v5)

```
arbiter-capital/
├── agents/
│   ├── quant.py                  # LangGraph + math tools + LLM + LLMContext capture
│   └── patriarch.py              # Constrained LLM + recompute + sim-oracle call
├── core/
│   ├── models.py                 # Proposal, Eval, Bundle, LLMContext, Sim*, Attack*
│   ├── network.py                # AXL client (live + SQLite mock)
│   ├── crypto.py                 # EIP-712 + sign + recover utilities
│   ├── identity.py               # OWNER_REGISTRY (incl. KeeperHub attestor)
│   ├── persistence.py            # CursorStore
│   ├── dedupe.py                 # DedupeLedger
│   ├── retry.py                  # Backoff helpers
│   └── market_god.py             # Synthetic scenarios
├── execution/
│   ├── firewall.py               # Deterministic policy gate (no LLM)
│   ├── safe_treasury.py          # Safe + sig assembly + nonce
│   ├── keeper_hub.py             # MCP client (Module + Sim Oracle)
│   └── uniswap_v4/
│       ├── router.py             # UR + Permit2 + v4 calldata
│       ├── universal_router.py   # UR command/input encoders
│       ├── permit2.py            # Permit2 SignatureTransfer
│       └── hooks.py              # Hook permission-bit validation
├── hooks/
│   └── ArbiterThrottleHook.sol   # ✱ v5: our own deployed v4 hook
├── contracts/
│   └── ArbiterReceipt.sol        # ✱ v5: SBT decision receipt
├── memory/
│   ├── memory_manager.py         # 0G writer (LLMContext + receipts) + ChromaDB
│   └── audit_chain.py            # Hash-chain head + verifier helpers
├── monitor/
│   ├── monitor_network.py        # CLI dashboard (multi-pane)
│   └── public_verifier/          # ✱ v5: static site for audience QR
├── scripts/
│   ├── enable_keeperhub_module.py
│   ├── deploy_throttle_hook.s.sol      # Foundry script
│   ├── deploy_arbiter_receipt.py
│   ├── replay_decision.py              # ✱ v5: deterministic LLM replay
│   ├── demo_run.py                     # Orchestrated demo script
│   └── chaos/                          # Chaos test scripts
├── byzantine_watchdog.py         # ✱ v5: 5th process, demo-only
├── quant_process.py
├── patriarch_process.py
├── execution_process.py
├── verify_audit.py
├── market_injector.py
├── state/                        # cursors, dedupe, pending_0g
└── tests/                        # pytest suite (must be green)
```

---

*End of SYSTEM_DESIGN.md v5.0 ("Winning Edition"). Cross-reference: `TECHNICAL_ROADMAP.md v5.0` for the day-by-day implementation plan from 2026-04-26 to 2026-05-06.*
