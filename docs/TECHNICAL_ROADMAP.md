# Arbiter Capital — Technical Roadmap & Implementation Plan (v5.0 — "Winning Sprint")

**Date of plan:** 2026-04-26
**Demo deadline:** 2026-05-06 (10 days)
**Target hackathon:** ETHGlobal Open Agents
**Companion doc:** `SYSTEM_DESIGN.md v5.0` (architecture spec — anything contradicting it is a bug in this roadmap)

This roadmap is a **drop-in implementation playbook**. v5.0 layers five elite features (custom v4 hook, 0G LLM memory substrate, KeeperHub simulation oracle, Byzantine Watchdog, Soulbound Decision Receipt) on top of the v4.0 hardening foundation. Every step lists (a) files to touch, (b) concrete signatures or pseudo-code, (c) acceptance criteria, (d) test plan.

---

## Table of Contents

- [0. Status Snapshot](#0-status-snapshot-as-of-2026-04-26)
- [1. Sprint Schedule (10-Day Countdown)](#1-sprint-schedule-10-day-countdown)
- [2. Day 1 — MVP 6.0: Critical Bug Triage](#2-day-1--mvp-60-critical-bug-triage)
  - [x] Step 0.1 — Fix `eth_account` signing API
  - [x] Step 0.2 — Fix web3 7.15 attribute
  - [x] Step 0.3 — Fix test suite collection
  - [ ] Step 0.4 — Live Gensyn AXL deployment ✱ compliance-6
  - [x] Step 0.5 — State directory + cursor persistence
- [3. Day 2 — MVP 6.1: EIP-712 + Identity Registry + Quant Signing + LLMContext Capture](#3-day-2--mvp-61-eip-712--identity-registry--quant-signing--llmcontext-capture)
  - [x] Step 1.1 — Crypto utilities
  - [x] Step 1.2 — Identity registry
  - [x] Step 1.3 — Extend Proposal model
  - [x] Step 1.4 — LLMContext model + capture helper
  - [x] Step 1.5 — Quant signs at end of LangGraph
  - [x] Step 1.6 — SafeTreasury upgrades
- [4. Day 3 — MVP 6.2: True 2-of-2 + ConsensusBundle + Dedupe](#4-day-3--mvp-62-true-2-of-2--consensusbundle--dedupe)
  - [x] Step 2.1 — Patriarch verifies, recomputes, then signs
  - [x] Step 2.2 — Dedupe ledger
  - [x] Step 2.3 — Execution Node — real verification
  - [x] Step 2.4 — Remove duplicate `time.sleep(2)`
- [5. Day 4 — MVP 6.3: Math-First Hardening](#5-day-4--mvp-63-math-first-hardening)
  - [x] Step 3.1 — Hash the Quant analysis
  - [x] Step 3.2 — Self-audit node
  - [x] Step 3.3 — Patriarch independently re-runs
  - [x] Step 3.4 — Constrain Patriarch LLM
  - [x] Step 3.5 — Decimals discipline everywhere
- [6. Day 5 — MVP 6.4: UR + Permit2 + ArbiterThrottleHook ✱ Elite-1](#6-day-5--mvp-64-ur--permit2--arbiterthrottlehook--elite-1)
  - [x] Step 4.1 — Pin all addresses Day-5 morning
  - [x] Step 4.2 — UR calldata builder
  - [x] Step 4.3 — Refactor `UniswapV4Router.generate_calldata`
  - [x] Step 4.4 — Permit2 helper
  - [ ] Step 4.5 — Deploy ArbiterThrottleHook ✱ elite-1
- [7. Day 6 — MVP 6.5: Sepolia Safe + KeeperHub Module + Sim Oracle ✱ Elite-3](#7-day-6--mvp-65-sepolia-safe--keeperhub-module--sim-oracle--elite-3)
  - [ ] Step 5.1 — Deploy 2-of-2 Safe on Sepolia
  - [x] Step 5.2 — Enable KeeperHub Module
  - [x] Step 5.3 — KeeperHub Sim Oracle ✱ elite-3
  - [ ] Step 5.4 — End-to-end live tx
  - [x] Step 5.5 — `langchain_keeperhub.py` bridge ✱ compliance-7
- [8. Day 7 — MVP 6.6: Hash-Chained Audit + 0G LLM Substrate ✱ Elite-2 + ArbiterReceipt SBT ✱ Elite-5a](#8-day-7--mvp-66-hash-chained-audit--0g-llm-substrate--elite-2--arbiterreceipt-sbt--elite-5a)
  - [x] Step 6.1 — Audit chain head pointer
  - [x] Step 6.2 — Receipt taxonomy
  - [x] Step 6.3 — MemoryManager writes the chain
  - [x] Step 6.4 — `replay_decision.py`
  - [x] Step 6.5 — Verifier walks the chain
  - [x] Step 6.6 — Reorg awareness
  - [x] Step 6.7 — ArbiterReceipt SBT ✱ elite-5a
- [9. Day 8 — MVP 7.0: Resilience + Byzantine Watchdog ✱ Elite-4 + Chaos](#9-day-8--mvp-70-resilience--byzantine-watchdog--elite-4--chaos)
  - [x] Step 7.1 — Heartbeats + reconnection backoff
  - [x] Step 7.2 — Byzantine Watchdog ✱ elite-4
  - [x] Step 7.3 — Chaos test scripts
- [10. Day 9 — MVP 7.1: Demo Polish + Public Verifier + QR ✱ Elite-5b](#10-day-9--mvp-71-demo-polish--public-verifier--qr--elite-5b)
  - [x] Step 8.1 — Multi-pane "God View" monitor
  - [x] Step 8.2 — Public verifier page ✱ elite-5b
  - [x] Step 8.3 — Demo orchestration script
  - [x] Step 8.4 — `docs/KEEPERHUB_FEEDBACK.md` ✱ compliance-8
  - [ ] Step 8.5 — Dress rehearsal
- [11. Day 10 — Submission](#11-day-10--submission)
  - [x] Step 9.0 — `scripts/check_bounty_compliance.py`
  - [ ] Step 9.1 — Final documentation
  - [ ] Step 9.2 — Final smoke test
  - [ ] Step 9.3 — Recording & submission
- [12. Risk Register](#12-risk-register)
- [13. Acceptance Criteria for Submission](#13-acceptance-criteria-for-submission)
- [14. Post-Hackathon (v6 backlog)](#14-post-hackathon-v6-backlog-not-in-scope)

---

## 0. Status Snapshot (as of 2026-04-26)

### What is **actually** implemented (real code in repo)
* Three-process daemon scaffold (`quant_process.py`, `patriarch_process.py`, `execution_process.py`) over a SQLite-backed `MockAXLNode`.
* Quant LangGraph with `calculate_optimal_rotation` math tool, ChromaDB recall, GPT-class proposal drafting.
* Patriarch LangGraph with single-shot LLM eval + deterministic post-LLM override.
* `PolicyFirewall` with whitelisted assets / max-USD / required-protocol checks.
* `MemoryManager` writes a "decision receipt" to local 0G storage (mock) or 0G L1 (live) and indexes embeddings in ChromaDB.
* `verify_audit.py` cross-references ChromaDB metadata against 0G testnet tx data.
* `monitor_network.py` rich CLI dashboard.
* `market_injector.py` + `core/market_god.py` for scenario injection.

### What is **claimed** but actually broken or stubbed
| Claim | Reality |
|---|---|
| "Cryptographic Consensus Signatures (COMPLETED)" | `SafeTreasury.sign_hash` calls `Account.sign_message(bytes)` — wrong eth_account API; raises `TypeError`. Correct call is `Account.unsafe_sign_hash`. |
| "Multisig Verification (COMPLETED)" | `execution_process.py:67` accepts the trade when `len(signatures) >= 1`. No `ecrecover`, no signer registry, no threshold ≥ 2. |
| "Real EVM calldata via `eth_abi`" | `UniswapV4Router.generate_calldata` uses placeholder selector `0x12345678` and direct `PoolManager.swap` ABI — not callable externally (requires unlock-callback). UR + Permit2 path missing. |
| "Live 0G Audit Trail" | `signed_tx.rawTransaction` — renamed to `raw_transaction` in web3 7.15. Live mode raises `AttributeError`. |
| Test suite green | `tests/test_execution.py` `sys.modules` mocks `eth_account` — breaks `web3.types`, suite fails at collection. Calls non-existent `treasury.execute_proposal`. |

### What is **missing** entirely (and what v5 adds)
**v4 fixes:** EIP-712 typed-data hashing, owner registry, persistent cursor + dedupe ledger, Patriarch math recompute, Patriarch context recall, Permit2 / UR / real v4 hook addresses, heartbeats, reconnection backoff, hash-chained audit log, reorg-aware verifier confirmations, decimals discipline, KeeperHub Module integration, per-asset allocation cap, daily drawdown cap, gas-price cap.

**v5 elite features:**
1. **🎯 ArbiterThrottleHook** — our own deployed v4 hook on Sepolia.
2. **🧠 0G LLM Memory Substrate** — full `LLMContext` artifacts on 0G + `replay_decision.py`.
3. **🛂 KeeperHub Simulation Oracle** — `simulate_safe_tx` MCP tool consumed by Patriarch *during* evaluation.
4. **🐺 Byzantine Watchdog** — 5th process publishing scripted attacks; system rejects on camera.
5. **🎟️ Soulbound Decision Receipt + QR verification** — ERC-721 SBT minted to Safe; public verifier page.

**v5.1 hackathon-compliance additions** (mandated by `docs/HACKATHON_DETAILS.md`):
6. **📡 Live AXL on the demo path** — Gensyn explicitly forbids centralized message brokers. Our SQLite mock is a centralized broker and is fail-closed when `DEMO_MODE=1`. Real Gensyn AXL nodes must be running for the recording.
7. **🔌 LangChain KeeperHub Bridge** — `langchain_keeperhub.py` exposing KeeperHub as a reusable `BaseTool` for any LangGraph project. This explicitly hits KeeperHub Focus Area 2 ("bridges/plugins for agent frameworks").
8. **📝 KeeperHub Builder Feedback** — `docs/KEEPERHUB_FEEDBACK.md` documenting UX friction encountered. Cheapest $250 in the prize pool.
9. **🎭 Agent Town Persona Framing** — recasting the architecture as a 4-persona Agent Town (Quant, Patriarch, Sim-Oracle Auditor, Byzantine Adversary), explicitly aligned with Gensyn's "Agent Town" track.

---

## 1. Sprint Schedule (10-Day Countdown)

| Day | Date | Track | Deliverable Headline |
|---|---|---|---|
| 1 | 2026-04-27 | **6.0** | Critical bug triage + state persistence skeleton + **live AXL nodes online** ✱ compliance-6 |
| 2 | 2026-04-28 | **6.1** | EIP-712 + identity registry + Quant signing + LLMContext capture |
| 3 | 2026-04-29 | **6.2** | True 2-of-2 + ConsensusBundle + dedupe ledger |
| 4 | 2026-04-30 | **6.3** | Math-first hardening (analysis hash, Patriarch recompute, decimals) |
| 5 | 2026-05-01 | **6.4** | UR + Permit2 + **ArbiterThrottleHook deploy** ✱ elite-1 |
| 6 | 2026-05-02 | **6.5** | Sepolia Safe + **KeeperHub Module + Sim Oracle** ✱ elite-3 + **`langchain_keeperhub.py` bridge** ✱ compliance-7 |
| 7 | 2026-05-03 | **6.6** | Hash-chained audit + **0G LLMContext substrate** ✱ elite-2 + **ArbiterReceipt SBT** ✱ elite-5a |
| 8 | 2026-05-04 | **7.0** | Resilience + **Byzantine Watchdog** ✱ elite-4 + chaos matrix |
| 9 | 2026-05-05 | **7.1** | Demo polish + **public verifier page + QR** ✱ elite-5b + **`KEEPERHUB_FEEDBACK.md`** ✱ compliance-8 + dress rehearsal |
| 10 | 2026-05-06 | Submit | Final docs + recorded video + **`scripts/check_bounty_compliance.py` green** + ETHGlobal submission |

**Go/no-go gate:** End of Day 8 — chaos matrix must pass and Watchdog rejection must produce green-on-camera evidence. If anything fails, Day 9 is reserved for triage; the bonus polish slips.

---

## 2. Day 1 — MVP 6.0: Critical Bug Triage

**Objective:** Stop the bleeding. Eliminate every silent failure surfaced by the audit. Establish `state/` directory.

### [x] Step 0.1 — Fix `eth_account` signing API
**File:** `execution/safe_treasury.py`

```python
# Replace sign_hash with:
def sign_hash(self, safe_tx_hash: str, key: bytes | None = None) -> str:
    """Sign a 32-byte EIP-712 digest. Use unsafe_sign_hash — Safe expects raw hash sigs."""
    signing_key = key if key is not None else self.executor_account.key
    digest = bytes.fromhex(safe_tx_hash[2:] if safe_tx_hash.startswith("0x") else safe_tx_hash)
    if len(digest) != 32:
        raise ValueError(f"safe_tx_hash must be 32 bytes, got {len(digest)}")
    signed = Account.unsafe_sign_hash(digest, signing_key)
    return signed.signature.hex()
```

**Acceptance:** `python -c "from execution.safe_treasury import SafeTreasury; t=SafeTreasury(); h=t.get_safe_tx_hash('0x'+'00'*20, b'test', 0); print(t.sign_hash(h))"` prints a 132-char hex string.

### [x] Step 0.2 — Fix web3 7.15 attribute
**File:** `memory/memory_manager.py`

`signed_tx.rawTransaction` → `signed_tx.raw_transaction`.

**Acceptance:** With valid `ZERO_G_RPC_URL` + funded `ZERO_G_PRIVATE_KEY`, `MemoryManager.save_decision(...)` returns a real 64-hex tx hash visible on the 0G explorer.

### [x] Step 0.3 — Fix test suite collection
**Files:** `tests/test_execution.py`, `tests/__init__.py`

* Remove `sys.modules` stubbing of `eth_account` (it cascades into `web3.types`).
* Set env vars to force mock mode.
* Replace the call to non-existent `treasury.execute_proposal(...)` with `treasury.execute_with_signatures(proposal, calldata, [sig])`.

**Acceptance:** `pytest tests/ -x` passes with ≥9 tests collected and 0 errors.

### [ ] Step 0.4 — Live Gensyn AXL deployment ✱ compliance-6 (DAY 1 PRIORITY)
**Why this is Day 1:** Gensyn's bounty has a hard requirement — "no centralized message brokers." Our current SQLite-backed `MockAXLNode` is a centralized broker. If the demo recording uses it, **we are disqualified from the Gensyn bounty by definition.** Live AXL must be running before any other elite-feature work, because every subsequent acceptance criterion runs against it.

**Files:** `scripts/setup_axl.sh` (new), `core/network.py` (modify).

```bash
# scripts/setup_axl.sh — bring up 5 distinct AXL nodes locally for demo path
#!/usr/bin/env bash
# Per Gensyn AXL docs (verify URL & exact CLI on Day 1 morning):
#   curl -L https://docs.gensyn.ai/axl/install.sh | bash
# OR follow whatever install path the AXL docs prescribe at hackathon time.

set -euo pipefail
PORTS=(9001 9002 9003 9004 9005)
NODE_IDS=("Quant_Node_A" "Patriarch_Node_B" "Execution_Node_P3" "KeeperHub_Sim_P4" "Adversary_Node_Z")
for i in "${!PORTS[@]}"; do
  axl-node \
    --listen "127.0.0.1:${PORTS[$i]}" \
    --node-id "${NODE_IDS[$i]}" \
    --keystore "./state/axl_keys/${NODE_IDS[$i]}.key" \
    --peers "127.0.0.1:9001,127.0.0.1:9002,127.0.0.1:9003,127.0.0.1:9004,127.0.0.1:9005" \
    --log-file "./state/axl_logs/${NODE_IDS[$i]}.log" &
  echo "Started ${NODE_IDS[$i]} on port ${PORTS[$i]} (pid $!)"
done
wait
```

> The exact AXL CLI flags must be verified against the live Gensyn docs on Day 1 morning. The intent above is invariant: **5 distinct AXL nodes**, **fully meshed**, **no shared database between them**.

Add `.env` mappings for each daemon:
```
AXL_NODE_URL_QUANT=http://127.0.0.1:9001
AXL_NODE_URL_PATRIARCH=http://127.0.0.1:9002
AXL_NODE_URL_EXEC=http://127.0.0.1:9003
AXL_NODE_URL_KEEPERHUB=http://127.0.0.1:9004
AXL_NODE_URL_WATCHDOG=http://127.0.0.1:9005
AXL_PEER_KEYS=<comma-separated peer pubkeys from setup>
DEMO_MODE=1
```

Each daemon now reads its own `AXL_NODE_URL_*` env var:
```python
# In quant_process.py:
axl_node = MockAXLNode(node_id="Quant_Node_A", url_env="AXL_NODE_URL_QUANT")
```

**Modify `core/network.py`:**
```python
def __init__(self, node_id: str, url_env: str = "AXL_NODE_URL"):
    self.node_id = node_id
    self.axl_url = os.getenv(url_env)
    self.use_live_axl = self.axl_url is not None
    self.demo_mode = os.getenv("DEMO_MODE") == "1"
    self._init_db()
    self._assert_demo_transport()
    if self.use_live_axl:
        logger.info(f"Node {node_id} initialized with LIVE AXL at {self.axl_url}")
    else:
        logger.info(f"Node {node_id} initialized in MOCK (SQLite) mode — DEV ONLY.")

def _assert_demo_transport(self) -> None:
    """Fail-closed if DEMO_MODE=1 and we'd silently fall back to SQLite."""
    if self.demo_mode and not self.use_live_axl:
        logger.error(
            f"DEMO_MODE=1 but {self.node_id} has no AXL_NODE_URL set. "
            "SQLite mock is a centralized broker and violates the Gensyn bounty's "
            "'no centralized message brokers' requirement. Refusing to start."
        )
        sys.exit(1)
```

**Acceptance:**
* `bash scripts/setup_axl.sh` brings up 5 nodes; `axl-node status` (or equivalent) shows all 5 healthy.
* `DEMO_MODE=1 python quant_process.py` (without setting `AXL_NODE_URL_QUANT`) **exits with code 1** and the compliance error message above.
* End-to-end run with all 5 daemons connected to their respective AXL nodes successfully exchanges a `MARKET_DATA → PROPOSALS → CONSENSUS_SIGNATURES → EXECUTION_SUCCESS` flow with 5 distinct senders visible on `monitor_network.py`.
* `monitor_network.py`'s "distinct senders in last 60s" counter shows ≥4 (5 once Watchdog runs).

### [x] Step 0.5 — State directory + cursor persistence
**New files:** `state/.gitkeep`, `core/persistence.py`

```python
# core/persistence.py
import json, os, threading
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_DIR.mkdir(exist_ok=True)
_LOCK = threading.Lock()

class CursorStore:
    def __init__(self, process_name: str):
        self.path = STATE_DIR / f"{process_name}.cursors.json"
        self._cache = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, topic: str) -> int: return int(self._cache.get(topic, 0))

    def set(self, topic: str, last_id: int) -> None:
        with _LOCK:
            self._cache[topic] = int(last_id)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._cache))
            os.replace(tmp, self.path)
```

Wire into all three daemons (`last_market_id = cursors.get("MARKET_DATA")` etc.). Add `state/` to `.gitignore`.

**Acceptance:** Kill `quant_process.py` mid-loop, restart, confirm via `monitor_network.py` that already-consumed market data is NOT re-processed.

---

## 3. Day 2 — MVP 6.1: EIP-712 + Identity Registry + Quant Signing + LLMContext Capture

**Objective:** Real EIP-712 typed-data hashing, identity registry, Quant signing both `bundle_hash` and `safe_tx_hash`, and **first 0G writes of `LLMContext` artifacts** (early start on the 0G elite feature).

### [x] Step 1.1 — Crypto utilities
**New file:** `core/crypto.py`

```python
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address

DOMAIN_NAME = "ArbiterCapital"
DOMAIN_VERSION = "1"

PROPOSAL_TYPES = {
    "Proposal": [
        {"name": "proposal_id",         "type": "string"},
        {"name": "iteration",           "type": "uint16"},
        {"name": "target_protocol",     "type": "string"},
        {"name": "v4_hook_required",    "type": "string"},
        {"name": "action",              "type": "string"},
        {"name": "asset_in",            "type": "address"},
        {"name": "asset_out",           "type": "address"},
        {"name": "amount_in_units",     "type": "uint256"},
        {"name": "min_amount_out_units","type": "uint256"},
        {"name": "deadline_unix",       "type": "uint64"},
        {"name": "projected_apy_bps",   "type": "uint32"},
        {"name": "risk_score_bps",      "type": "uint16"},
        {"name": "quant_analysis_hash", "type": "bytes32"},
        {"name": "market_snapshot_hash","type": "bytes32"},
        {"name": "llm_context_hash",    "type": "bytes32"},
        {"name": "safe_nonce",          "type": "uint256"},
    ]
}

def proposal_eip712_digest(p_dict: dict, verifying_contract: str, chain_id: int) -> bytes:
    domain = {"name": DOMAIN_NAME, "version": DOMAIN_VERSION,
              "chainId": chain_id, "verifyingContract": to_checksum_address(verifying_contract)}
    return encode_typed_data(domain, PROPOSAL_TYPES, "Proposal", p_dict).body

def bundle_hash(proposal_hash: bytes, safe_tx_hash: bytes) -> bytes:
    return keccak(proposal_hash + safe_tx_hash)

def sign_digest(digest: bytes, private_key: bytes) -> str:
    return Account.unsafe_sign_hash(digest, private_key).signature.hex()

def recover_signer(digest: bytes, sig_hex: str) -> str:
    sig = sig_hex if sig_hex.startswith("0x") else "0x" + sig_hex
    return to_checksum_address(Account._recover_hash(digest, signature=sig))
```

### [x] Step 1.2 — Identity registry
**New file:** `core/identity.py`

```python
import os
from eth_account import Account
from eth_utils import to_checksum_address

def _key(env: str) -> bytes | None:
    v = os.getenv(env)
    if not v or v.startswith("0xabc") or v == "0x" + "0"*64:
        return None
    return bytes.fromhex(v[2:] if v.startswith("0x") else v)

QUANT_KEY      = _key("QUANT_PRIVATE_KEY")
PATRIARCH_KEY  = _key("PATRIARCH_PRIVATE_KEY")
EXECUTOR_KEY   = _key("EXECUTOR_PRIVATE_KEY")
KEEPERHUB_KEY  = _key("KEEPERHUB_ATTESTOR_KEY")     # v5: sim oracle attestor

def _addr(k): return to_checksum_address(Account.from_key(k).address) if k else None

QUANT_ADDR     = _addr(QUANT_KEY)
PATRIARCH_ADDR = _addr(PATRIARCH_KEY)
EXECUTOR_ADDR  = _addr(EXECUTOR_KEY)
KEEPERHUB_ADDR = _addr(KEEPERHUB_KEY)

# Safe-owner registry (only these two can sign for execution)
SAFE_OWNERS: dict[str, str] = {}
if QUANT_ADDR:     SAFE_OWNERS[QUANT_ADDR]     = "Quant_Node_A"
if PATRIARCH_ADDR: SAFE_OWNERS[PATRIARCH_ADDR] = "Patriarch_Node_B"

# Attestor registry (advisory signers like KeeperHub Sim Oracle)
ATTESTORS: dict[str, str] = {}
if KEEPERHUB_ADDR: ATTESTORS[KEEPERHUB_ADDR] = "KeeperHub_Sim_Oracle"

def is_safe_owner(addr: str) -> bool:    return to_checksum_address(addr) in SAFE_OWNERS
def is_attestor(addr: str) -> bool:      return to_checksum_address(addr) in ATTESTORS
```

Update `.env.example` with `QUANT_PRIVATE_KEY`, `PATRIARCH_PRIVATE_KEY`, `EXECUTOR_PRIVATE_KEY`, `KEEPERHUB_ATTESTOR_KEY`.

### [x] Step 1.3 — Extend Proposal model
**File:** `core/models.py`

Add fields per `SYSTEM_DESIGN §4.1`: `parent_proposal_id`, `iteration`, `amount_in_units`, decimals, `min_amount_out_units`, `deadline_unix`, `*_bps` ints, `quant_analysis_hash`, `market_snapshot_hash`, `llm_context_hash`, `llm_context_0g_tx`, `proposal_hash`, `safe_tx_hash`, `quant_signature`, `patriarch_signature`, `safe_nonce`, `chain_id`. Keep legacy fields for back-compat with migration validator.

```python
DECIMALS_BY_SYMBOL = {"WETH":18, "stETH":18, "USDC":6, "WBTC":8, "PT-USDC":6, "SOL":9}

@model_validator(mode="after")
def _populate(self):
    if self.amount_in_units is None and self.amount_in is not None:
        d = self.asset_in_decimals or DECIMALS_BY_SYMBOL.get(self.asset_in, 18)
        self.amount_in_units = str(int(self.amount_in * (10**d)))
        self.asset_in_decimals = d
    if self.projected_apy_bps is None and self.projected_apy is not None:
        self.projected_apy_bps = int(self.projected_apy * 100)
    if self.risk_score_bps is None and self.risk_score_evaluation is not None:
        self.risk_score_bps = int(self.risk_score_evaluation * 1000)
    return self
```

### [x] Step 1.4 — LLMContext model + capture helper (v5 elite-2 starts here)
**File:** `core/models.py`

```python
class LLMContext(BaseModel):
    schema_version: int = 1
    call_id: str
    invoking_agent: Literal["Quant_Node_A", "Patriarch_Node_B"]
    invoked_at: float
    proposal_id: str
    iteration: int
    model_id: str
    temperature: float
    seed: Optional[int] = None
    structured_output_schema_hash: str
    structured_output_schema_name: str
    system_prompt: str
    messages: list[dict]
    response_raw: str
    response_parsed_hash: str
    tools_invoked: list[str] = []
    context_hash: str
```

**New file:** `memory/llm_context_writer.py`

```python
import json, time, uuid
from eth_utils import keccak
from core.models import LLMContext
from memory.memory_manager import MemoryManager

def capture_and_persist(*, agent, proposal_id, iteration, model_id, temperature, seed,
                       schema, schema_name, system_prompt, messages, response_raw, parsed_obj,
                       tools_invoked) -> tuple[str, str]:
    """Build LLMContext, write to 0G, return (context_hash, 0g_tx_hash)."""
    parsed_canonical = json.dumps(parsed_obj.model_dump(), sort_keys=True, separators=(",",":")).encode()
    schema_canonical = json.dumps(schema, sort_keys=True, separators=(",",":")).encode()
    body = {
        "schema_version": 1,
        "call_id": uuid.uuid4().hex,
        "invoking_agent": agent,
        "invoked_at": time.time(),
        "proposal_id": proposal_id,
        "iteration": iteration,
        "model_id": model_id,
        "temperature": temperature,
        "seed": seed,
        "structured_output_schema_hash": "0x" + keccak(schema_canonical).hex(),
        "structured_output_schema_name": schema_name,
        "system_prompt": system_prompt,
        "messages": messages,
        "response_raw": response_raw,
        "response_parsed_hash": "0x" + keccak(parsed_canonical).hex(),
        "tools_invoked": tools_invoked,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",",":")).encode()
    body["context_hash"] = "0x" + keccak(canonical).hex()
    ctx = LLMContext(**body)
    mm = MemoryManager()
    tx_hash = mm.write_artifact("LLMContext", ctx.model_dump())
    return body["context_hash"], tx_hash
```

`MemoryManager.write_artifact(kind, payload)` is a generic write that returns the 0G tx hash. Wire it into the existing `_write_to_0g` infrastructure.

### [x] Step 1.5 — Quant signs at end of LangGraph
**File:** `agents/quant.py`

Add nodes: `capture_llm_context` (after `draft_proposal_llm`) and `sign_proposal` (after `self_audit`). The `draft_proposal_llm` node now records `(system_prompt, messages, response_raw, parsed_obj)` into `state` so `capture_llm_context` can persist them.

```python
def sign_proposal(state):
    p: Proposal = state["current_proposal"]
    if p is None: return {}
    treasury = SafeTreasury()
    router = UniswapV4Router()
    calldata = router.generate_calldata(p)
    p.safe_nonce = treasury.read_nonce()
    p.safe_tx_hash = treasury.get_safe_tx_hash(treasury.target_address(), calldata, 0, nonce=p.safe_nonce)
    p_digest = proposal_eip712_digest(p.model_dump(by_alias=True), treasury.safe_address, p.chain_id)
    p.proposal_hash = "0x" + p_digest.hex()
    bdigest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
    sig_bundle = sign_digest(bdigest, QUANT_KEY)
    sig_safe   = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), QUANT_KEY)
    p.quant_signature = sig_bundle + sig_safe[2:]
    return {"current_proposal": p}
```

### [x] Step 1.6 — SafeTreasury upgrades
**File:** `execution/safe_treasury.py`

Add `target_address()`, `read_nonce()`, EIP-712-aware `get_safe_tx_hash(to, data, value, nonce)`. Mock-mode hash now includes `nonce` and `chain_id` to avoid replay collisions. Fix `safe.build_multisig_tx` to pass `safe_nonce=nonce`.

**Acceptance for Day 2:**
* `python quant_process.py` (with `QUANT_PRIVATE_KEY` set) emits a Proposal whose `recover_signer(p_digest, sig_bundle) == QUANT_ADDR`.
* For each LLM call, an `LLMContext` artifact is written to 0G; the tx hash is reachable from the Proposal via `llm_context_0g_tx`.
* `python -c "from memory.memory_manager import MemoryManager; m=MemoryManager(); print(m.read_artifact('<tx_hash>'))"` returns the original `LLMContext` JSON.

---

## 4. Day 3 — MVP 6.2: True 2-of-2 + ConsensusBundle + Dedupe

**Objective:** Replace `len(sigs) >= 1` with real cryptographic threshold verification.

### [x] Step 2.1 — Patriarch verifies, recomputes, then signs
**File:** `patriarch_process.py`

```python
# 1. Verify Quant's bundle signature
sig_bundle_q = "0x" + p.quant_signature[2:132]
sig_safe_q   = "0x" + p.quant_signature[132:]
p_digest = proposal_eip712_digest(p.model_dump(by_alias=True), treasury.safe_address, p.chain_id)
b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
if recover_signer(b_digest, sig_bundle_q) != QUANT_ADDR:
    publish_attack_rejection(p, "INVALID_SIGNATURE", "Quant bundle sig mismatch.")
    continue
if recover_signer(bytes.fromhex(p.safe_tx_hash[2:]), sig_safe_q) != QUANT_ADDR:
    publish_attack_rejection(p, "INVALID_SIGNATURE", "Quant safe sig mismatch.")
    continue

# 2. Run patriarch_app (with sim oracle call — see Day 6)
# 3. On accept, sign both digests
sig_bundle_p = sign_digest(b_digest, PATRIARCH_KEY)
sig_safe_p   = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), PATRIARCH_KEY)
reviewed.patriarch_signature = sig_bundle_p + sig_safe_p[2:]

# 4. Publish ConsensusMessage and FIREWALL_CLEARED
```

`publish_attack_rejection(p, kind, reason)` is a new helper that publishes `ATTACK_REJECTED` to AXL **and** writes an `AttackRejection` to 0G. (Used for both Watchdog rejections in Day 8 and any natural rejection here.)

### [x] Step 2.2 — Dedupe ledger
**New file:** `core/dedupe.py`

```python
import sqlite3, time
from core.persistence import STATE_DIR

class DedupeLedger:
    def __init__(self):
        self.path = STATE_DIR / "executed_proposals.sqlite"
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS executed (
                safe_address TEXT, safe_nonce INTEGER, proposal_id TEXT,
                tx_hash TEXT, status TEXT, ts REAL,
                PRIMARY KEY (safe_address, safe_nonce))""")

    def already_executed(self, safe_address: str, safe_nonce: int) -> bool:
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT 1 FROM executed WHERE safe_address=? AND safe_nonce=?",
                             (safe_address, safe_nonce)).fetchone() is not None

    def mark(self, safe_address, safe_nonce, proposal_id, tx_hash, status="OK"):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT OR REPLACE INTO executed VALUES (?,?,?,?,?,?)",
                      (safe_address, safe_nonce, proposal_id, tx_hash, status, time.time()))
```

### [x] Step 2.3 — Execution Node — real verification
**File:** `execution_process.py`

```python
THRESHOLD = int(os.getenv("CONSENSUS_THRESHOLD", "2"))

def verify_threshold(p: Proposal, sigs: list[ConsensusMessage]) -> tuple[bool, list[str]]:
    seen = set()
    safe_h = bytes.fromhex(p.safe_tx_hash[2:])
    for m in sigs:
        addr = recover_signer(safe_h, m.signature)
        if addr in SAFE_OWNERS and addr not in seen:
            seen.add(addr)
    return (len(seen) >= THRESHOLD, sorted(seen, key=lambda a: int(a, 16)))

# In loop:
ok, signers = verify_threshold(proposal, [ConsensusMessage(**s) for s in raw_sigs])
if not ok: continue
if dedupe.already_executed(treasury.safe_address, proposal.safe_nonce):
    publish_attack_rejection(proposal, "REPLAY_NONCE", f"nonce {proposal.safe_nonce} already used")
    del pending_proposals[proposal.proposal_id]; continue

# Build Safe-format signatures (sorted by signer addr ascending)
sigs_blob = b""
for addr in signers:
    sig = next(s.signature for s in sigs if recover_signer(safe_h, s.signature) == addr)
    sigs_blob += bytes.fromhex(sig[2:])
tx_hash = treasury.execute_with_signatures(proposal, calldata, sigs_blob)
dedupe.mark(treasury.safe_address, proposal.safe_nonce, proposal.proposal_id, tx_hash)
```

### [x] Step 2.4 — Remove duplicate `time.sleep(2)` at `execution_process.py:94-96`.

**Acceptance:**
* End-to-end run dispatches only when both signatures recover to `SAFE_OWNERS`.
* Replay of the same `CONSENSUS_SIGNATURES` does not double-execute.
* Killing the Execution Node after 1 sig collected, restarting → 2-of-2 collection completes once.

---

## 5. Day 4 — MVP 6.3: Math-First Hardening

**Objective:** Eliminate LLM ability to fabricate quantitative fields.

### [x] Step 3.1 — Hash the Quant analysis
**File:** `agents/quant.py`

```python
def quantitative_ingestion(state):
    md = state.get("market_data", generate_market_data("normal"))
    a = calculate_optimal_rotation(md)
    canonical = json.dumps(a, sort_keys=True, separators=(",",":")).encode()
    snapshot_canonical = json.dumps(md, sort_keys=True, separators=(",",":")).encode()
    return {
        "market_data": md,
        "quant_analysis": a,
        "quant_analysis_hash": "0x" + keccak(canonical).hex(),
        "market_snapshot_hash": "0x" + keccak(snapshot_canonical).hex(),
        "iteration": state.get("iteration", 0) + 1,
    }
```

The Quant publishes the original `MarketSnapshot` to AXL topic `MARKET_SNAPSHOTS` keyed by hash; Patriarch fetches by hash before recomputing.

### [x] Step 3.2 — Self-audit node
```python
def self_audit(state):
    p, a = state["current_proposal"], state["quant_analysis"]
    if p is None: return {}
    if p.projected_apy_bps != int(a.get("projected_apy", 0)*100): return {"current_proposal": None}
    if p.risk_score_bps != int(a.get("risk_score", 0)*1000): return {"current_proposal": None}
    if p.quant_analysis_hash != state["quant_analysis_hash"]: return {"current_proposal": None}
    return {}
```

### [x] Step 3.3 — Patriarch independently re-runs
**File:** `agents/patriarch.py`

```python
def deterministic_recheck(state):
    p, md = state["incoming_proposal"], state["market_data"]
    if not md: return {"reviewed_proposal": _reject(p, "MATH_MISMATCH", "no market_data")}
    a = calculate_optimal_rotation(md)
    canonical = json.dumps(a, sort_keys=True, separators=(",",":")).encode()
    expected = "0x" + keccak(canonical).hex()
    if expected != p.quant_analysis_hash:
        return {"reviewed_proposal": _reject(p, "MATH_MISMATCH",
            f"recomputed {expected}, claimed {p.quant_analysis_hash}")}
    return {"patriarch_recompute": a}
```

### [x] Step 3.4 — Constrain Patriarch LLM
```python
class ProposalEvaluation(BaseModel):
    proposal_id: str
    iteration: int
    consensus_status: Literal["ACCEPTED","REJECTED"]
    rejection_reason: Optional[Literal[
        "RISK_OVERRUN","MATH_MISMATCH","OUTSIDE_MANDATE","GAS_INEFFICIENT",
        "WHITELIST_VIOLATION","TIMING_RISK","SIM_REVERT","OTHER"]] = None
    rejection_detail: Optional[str] = None

structured_llm = llm.with_structured_output(ProposalEvaluation)
ev = structured_llm.invoke(messages)
reviewed = p.model_copy(deep=True)
reviewed.consensus_status = ConsensusStatus(ev.consensus_status)
# numeric fields are NEVER copied from ev — LLM cannot rewrite them
```

The Patriarch's LLM call is also wrapped in `capture_and_persist(...)` so its `LLMContext` lands on 0G.

### [x] Step 3.5 — Decimals discipline everywhere
**File:** `execution/uniswap_v4/router.py`

Replace every `int(proposal.amount_in * 1e18)` with `int(proposal.amount_in_units)`. Resolve placeholder addresses (`stETH`, etc.) to real Sepolia addresses pinned in `.env`.

**Acceptance:**
* End-to-end with `pendle_yield_arbitrage` produces USDC `amount_in_units` in 6-decimal units (`"10000000000"` for 10,000 USDC).
* Tampering `Proposal.projected_apy_bps` post-draft causes self-audit to drop the proposal.
* Tampered `quant_analysis_hash` produces Patriarch `MATH_MISMATCH`.

---

## 6. Day 5 — MVP 6.4: UR + Permit2 + ArbiterThrottleHook ✱ Elite-1

**Objective:** Real Universal Router calldata. **Deploy our own v4 hook on Sepolia.**

### [ ] Step 4.1 — Pin all addresses Day-5 morning
Resolve from official Uniswap v4 deployment registry:
* `UNIVERSAL_ROUTER_ADDRESS`
* `V4_POOL_MANAGER` (already known: `0x000000000004444c5dc75cb358380d2e3de08a90`)
* `PERMIT2_ADDRESS = 0x000000000022D473030F116dDEE9F6B43aC78BA3`
* `V4_HOOK_VOL_ORACLE` (deployed reference hook)
* `V4_HOOK_DYNAMIC_FEE` (deployed reference hook)
* Sepolia token addresses (WETH, USDC, stETH, WBTC, PT-USDC)

### [x] Step 4.2 — UR calldata builder
**New file:** `execution/uniswap_v4/universal_router.py`

```python
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector

CMD_V4_SWAP        = 0x10
CMD_PERMIT2_PERMIT = 0x0A
UR_EXEC_SELECTOR = function_signature_to_4byte_selector("execute(bytes,bytes[],uint256)")

MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

def build_v4_swap_input(pool_key, swap_params, hook_data: bytes) -> bytes:
    return encode(
        ["(address,address,uint24,int24,address)", "(bool,int256,uint160)", "bytes"],
        [pool_key, swap_params, hook_data])

def build_permit2_input(token, amount_units, expiration, nonce, spender, sig):
    return encode(
        ["(address,uint160,uint48,uint48)", "address", "bytes"],
        [(token, amount_units, expiration, nonce), spender, sig])

def build_ur_execute_calldata(commands: bytes, inputs: list[bytes], deadline: int) -> bytes:
    body = encode(["bytes", "bytes[]", "uint256"], [commands, inputs, deadline])
    return UR_EXEC_SELECTOR + body
```

### [x] Step 4.3 — Refactor `UniswapV4Router.generate_calldata`
Build `PoolKey` (canonical-ordered), derive `zero_for_one`, set `amount_specified = -int(amount_in_units)` for exact-input, set `sqrt_price_limit` from slippage, build `V4_SWAP` input, prepend optional `PERMIT2_PERMIT`, return `build_ur_execute_calldata(...)`.

### [x] Step 4.4 — Permit2 helper
**New file:** `execution/uniswap_v4/permit2.py`

`ensure_permit2_approval(asset, amount, spender)` reads current allowance via `Permit2.allowance(safe, token, spender)`; if insufficient, builds and prepends a `PERMIT2_PERMIT` command with bounded amount + 24h expiry.

### [ ] Step 4.5 — **Deploy ArbiterThrottleHook (elite-1)**
**New files:**
* `hooks/ArbiterThrottleHook.sol` (Solidity per `SYSTEM_DESIGN §10.3`)
* `hooks/HookMiner.s.sol` (Foundry script — mine CREATE2 salt yielding correct permission bits)
* `script/DeployThrottleHook.s.sol`

```bash
# Foundry workflow (run on Day 5):
forge install Uniswap/v4-core
forge install Uniswap/v4-periphery
forge install OpenZeppelin/openzeppelin-contracts

# Mine the salt
forge script hooks/HookMiner.s.sol --rpc-url $SEPOLIA_RPC -vvv

# Deploy
forge script script/DeployThrottleHook.s.sol \
    --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_KEY --broadcast --verify

# Pin address in .env
echo "ARBITER_THROTTLE_HOOK=0x..." >> .env
```

**Add to firewall** (`execution/firewall.py`):
```python
ALLOWED_HOOKS = {
    os.getenv("V4_HOOK_VOL_ORACLE"),
    os.getenv("V4_HOOK_DYNAMIC_FEE"),
    os.getenv("ARBITER_THROTTLE_HOOK"),
    "0x" + "0"*40,
}
# bit-level permission validation
def validate_hook_address(hook_addr: str, expected_flags: int) -> bool:
    addr_int = int(hook_addr, 16)
    return (addr_int & 0x3FFF) & expected_flags == expected_flags
```

**Add to `core/market_god.py`:** a new scenario `arbiter_self_mev_attempt` that produces back-to-back proposals to demonstrate the throttle hook rejecting the second one (can be used in chaos tests).

**Acceptance:**
* `cast call $UR "execute(bytes,bytes[],uint256)" $generated_calldata` against Sepolia returns without revert (read-only simulation).
* `ARBITER_THROTTLE_HOOK` has the correct permission bits set (verifiable via `cast call $POOL_MANAGER`).
* Two consecutive Arbiter swaps within `minIntervalSeconds` cause the second to revert with `ArbiterThrottle: cooldown` (verified via Foundry test in `tests/forge/`).

---

## 7. Day 6 — MVP 6.5: Sepolia Safe + KeeperHub Module + Sim Oracle ✱ Elite-3

**Objective:** Real on-chain execution against a 2-of-2 Sepolia Safe. **KeeperHub becomes a consensus participant via the Sim Oracle MCP tool.**

### [ ] Step 5.1 — Deploy 2-of-2 Safe on Sepolia
Via `app.safe.global?chain=sep`. Owners: `[QUANT_ADDR, PATRIARCH_ADDR]`. Threshold: 2. Fund: 0.1 WETH, 100 USDC, 0.1 stETH, 0.01 WBTC. Pin `SAFE_ADDRESS` in `.env`.

### [x] Step 5.2 — Enable KeeperHub Module
**File:** `scripts/enable_keeperhub_module.py`

Module `0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D` enabled on Safe via 2-of-3 (Quant + Patriarch signatures).
Tx: `0x7cd80e05dbb594f70cf6439c168817eb873d9b12811c4a988049a10a01a3f30b` — Sepolia block 10775996.

### [ ] Step 5.3 — KeeperHub Sim Oracle (the elite move)
**File:** `execution/keeper_hub.py`

The KeeperHub MCP server now exposes:
* `simulate_safe_tx(to, value, data, op) → SimulationResult` — forks Sepolia at latest, applies `Safe.execTransactionFromModule`, returns success/revert/return-data, signs result with `KEEPERHUB_ATTESTOR_KEY`.
* `get_safe_nonce()` — authoritative read.
* `verify_module_enabled()` — boot health check.
* `execute_safe_transaction(to, value, data, signatures)` — final on-chain submit.

**File:** `agents/patriarch.py` — add `consult_sim_oracle` LangGraph node:

```python
def consult_sim_oracle(state):
    p = state["incoming_proposal"]
    if state.get("evaluation_pre_sim").consensus_status != "ACCEPTED":
        return {}  # rejection already; no sim needed
    req = SimulationRequest(
        request_id=uuid.uuid4().hex,
        proposal_id=p.proposal_id,
        iteration=p.iteration,
        safe_address=os.getenv("SAFE_ADDRESS"),
        to=os.getenv("UNIVERSAL_ROUTER_ADDRESS"),
        value=0,
        data="0x" + UniswapV4Router().generate_calldata(p).hex(),
        operation=0,
        requested_by="Patriarch_Node_B",
        timestamp=time.time(),
    )
    axl_node.publish("SIM_ORACLE_REQUEST", req.model_dump())
    deadline = time.time() + 8.0
    result = None
    while time.time() < deadline:
        msgs = axl_node.subscribe("SIM_ORACLE_RESULT", last_id=last_sim_id)
        for m in msgs:
            r = SimulationResult(**m["payload"])
            if r.request_id == req.request_id:
                result = r; break
        if result: break
        time.sleep(0.25)
    if not result:
        return {"reviewed_proposal": _reject(p, "OUTSIDE_MANDATE", "Sim oracle timeout")}
    # Verify KeeperHub signature
    sim_digest = keccak(json.dumps(result.model_dump(exclude={"simulator_signature"}),
                                    sort_keys=True, separators=(",",":")).encode())
    sim_signer = recover_signer(sim_digest, result.simulator_signature)
    if not is_attestor(sim_signer):
        return {"reviewed_proposal": _reject(p, "OUTSIDE_MANDATE", "Sim sig not from registered attestor")}
    if not result.success:
        return {"reviewed_proposal": _reject(p, "SIM_REVERT", result.revert_reason or "")}
    return {"sim_result": result.model_dump()}
```

The graph order becomes: `deterministic_recheck → evaluate_llm → consult_sim_oracle → finalize`. The sim result is included in the `NegotiationTranscript` written to 0G.

### [ ] Step 5.4 — End-to-end live tx
1. `python market_injector.py flash_crash_eth`.
2. Quant publishes signed Proposal + LLMContext on 0G.
3. Patriarch verifies, recomputes, evaluates, calls Sim Oracle, signs.
4. Execution Node assembles 2-of-2, calls KeeperHub.
5. KeeperHub `execTransaction` on Sepolia.
6. Tx hash returned, recorded.

**Acceptance:**
* Sepolia explorer shows real swap from Safe → UR → PoolManager (with `ArbiterThrottleHook` on the path).
* `verify_audit.py` confirms the on-chain receipt + chain link + sim oracle signature.
* Re-injecting same `safe_nonce` is rejected by dedupe + watchdog-style `ATTACK_REJECTED`.

### [x] Step 5.5 — `langchain_keeperhub.py` bridge ✱ compliance-7 (KeeperHub Focus Area 2)

KeeperHub's bounty has two focus areas. Step 5.3 hits **Focus Area 1** ("real problem via MCP"). This step hits **Focus Area 2** ("bridges/plugins for agent frameworks like LangChain"). Cost: ~2 hours; reward: doubled bounty surface and a public artifact other LangGraph builders can reuse.

**New file:** `langchain_keeperhub.py` (top-level — importable as `from langchain_keeperhub import KeeperHubExecuteTool`)

```python
"""
LangChain bridge for KeeperHub MCP. Exposes KeeperHub as reusable LangChain tools
for any LangGraph project — not just Arbiter Capital.

Usage in any LangGraph agent:
    from langchain_keeperhub import KeeperHubExecuteTool, KeeperHubSimulateTool
    tools = [KeeperHubSimulateTool(), KeeperHubExecuteTool()]
    agent = create_react_agent(llm, tools)

Configuration via env:
    KEEPERHUB_SERVER_PATH    - path to the KeeperHub MCP server binary
    SAFE_ADDRESS             - the Safe to operate on
    KEEPERHUB_ATTESTOR_KEY   - the attestor key (for verifying simulation signatures)
"""
from __future__ import annotations
import asyncio, os, json
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class _SimulateInput(BaseModel):
    to: str = Field(..., description="Target contract address (checksummed hex).")
    value: int = Field(0, description="Wei to send.")
    data_hex: str = Field(..., description="Calldata hex (with or without 0x prefix).")
    operation: int = Field(0, description="0=CALL, 1=DELEGATECALL.")


class _ExecuteInput(_SimulateInput):
    signatures_hex: str = Field(..., description="Concatenated Safe-format signatures.")


async def _mcp_call(tool_name: str, args: dict) -> dict:
    server_path = os.environ["KEEPERHUB_SERVER_PATH"]
    params = StdioServerParameters(command="node", args=[server_path], env=os.environ.copy())
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=args)
            if result is None or not result.content:
                raise RuntimeError(f"KeeperHub MCP returned empty response for {tool_name}")
            return json.loads(result.content[0].text)


class KeeperHubSimulateTool(BaseTool):
    name: str = "keeperhub_simulate_safe_tx"
    description: str = (
        "Simulate a Safe transaction by forking the latest chain state via KeeperHub. "
        "Returns success / revert + return data. Use this to verify a tx will succeed "
        "before paying gas to broadcast it."
    )
    args_schema: type[BaseModel] = _SimulateInput

    def _run(self, **kwargs) -> str:  # sync entry-point
        return json.dumps(asyncio.run(self._arun(**kwargs)))

    async def _arun(self, **kwargs) -> dict:
        kwargs["safe_address"] = os.environ["SAFE_ADDRESS"]
        return await _mcp_call("simulate_safe_tx", kwargs)


class KeeperHubExecuteTool(BaseTool):
    name: str = "keeperhub_execute_safe_transaction"
    description: str = (
        "Broadcast a fully-signed Safe transaction via KeeperHub's reliable execution layer. "
        "Caller must have already collected threshold signatures."
    )
    args_schema: type[BaseModel] = _ExecuteInput

    def _run(self, **kwargs) -> str:
        return json.dumps(asyncio.run(self._arun(**kwargs)))

    async def _arun(self, **kwargs) -> dict:
        kwargs["safe_address"] = os.environ["SAFE_ADDRESS"]
        return await _mcp_call("execute_safe_transaction", kwargs)
```

**Wire into `agents/patriarch.py`** so the Sim Oracle node uses the LangChain tool (not the bespoke MCP client) — eats our own dog food and proves the bridge works in production:

```python
from langchain_keeperhub import KeeperHubSimulateTool
sim_tool = KeeperHubSimulateTool()

async def consult_sim_oracle(state):
    # ...
    raw = await sim_tool.ainvoke({
        "to": os.getenv("UNIVERSAL_ROUTER_ADDRESS"),
        "value": 0,
        "data_hex": "0x" + UniswapV4Router().generate_calldata(p).hex(),
        "operation": 0,
    })
    sim_result = SimulationResult(**json.loads(raw))
    # ...
```

Add `tests/test_langchain_keeperhub.py` with a stubbed MCP server fixture; the test asserts `isinstance(KeeperHubSimulateTool(), BaseTool)` and that the schema validates correctly.

**Acceptance:**
* `python -c "from langchain_keeperhub import KeeperHubSimulateTool; from langchain_core.tools import BaseTool; assert isinstance(KeeperHubSimulateTool(), BaseTool)"` exits 0.
* The Patriarch's sim-oracle path goes through `langchain_keeperhub.KeeperHubSimulateTool.ainvoke` (verifiable via log of the LangChain callback handler).
* `pytest tests/test_langchain_keeperhub.py` passes.

---

## 8. Day 7 — MVP 6.6: Hash-Chained Audit + 0G LLM Substrate ✱ Elite-2 + ArbiterReceipt SBT ✱ Elite-5a

**Objective:** Make the audit log tamper-evident. Make 0G the **canonical AI memory substrate**. Mint SBTs.

### [x] Step 6.1 — Audit chain head pointer
**New file:** `memory/audit_chain.py`

```python
import json, time
from core.persistence import STATE_DIR
HEAD = STATE_DIR / "audit_chain_head.json"

class AuditChainHead:
    def __init__(self):
        self._c = json.loads(HEAD.read_text()) if HEAD.exists() else {"head": None}
    @property
    def head(self): return self._c.get("head")
    def advance(self, h):
        self._c = {"head": h, "updated": time.time()}
        HEAD.write_text(json.dumps(self._c))
```

### [x] Step 6.2 — Receipt taxonomy
**File:** `core/models.py`

```python
class BaseReceipt(BaseModel):
    schema_version: int = 5
    receipt_type: Literal["LLMContext","MarketSnapshot","NegotiationTranscript",
                          "DecisionReceipt","ExecutionReceipt","RejectionReceipt","AttackRejection"]
    receipt_id: str
    timestamp: float
    prev_0g_tx_hash: Optional[str] = None
    receipt_hash: str
    payload: dict
```

### [x] Step 6.3 — MemoryManager writes the chain
**File:** `memory/memory_manager.py`

```python
from memory.audit_chain import AuditChainHead

def write_artifact(self, kind: str, payload: dict) -> str:
    head = AuditChainHead()
    receipt = {
        "schema_version": 5, "receipt_type": kind, "receipt_id": uuid.uuid4().hex,
        "timestamp": time.time(), "prev_0g_tx_hash": head.head, "payload": payload,
    }
    canonical = json.dumps({k:v for k,v in receipt.items() if k != "receipt_hash"},
                           sort_keys=True, separators=(",",":")).encode()
    receipt["receipt_hash"] = "0x" + keccak(canonical).hex()
    tx_hash = self._write_to_0g(receipt)
    head.advance(tx_hash)
    # ChromaDB index
    if kind in ("DecisionReceipt", "LLMContext", "NegotiationTranscript"):
        self._index_chroma(receipt, tx_hash)
    return tx_hash
```

### [x] Step 6.4 — `replay_decision.py` (the elite-2 demo asset)
**New file:** `scripts/replay_decision.py`

```python
"""
Re-issue any past LLM call from 0G storage and verify deterministic match.
Usage:
  python scripts/replay_decision.py --proposal-id prop_8f72c
  python scripts/replay_decision.py --tx 0xabc...
"""
import argparse, json, hashlib
from openai import OpenAI
from web3 import Web3
from eth_utils import keccak
from memory.memory_manager import MemoryManager

def replay(tx_hash: str):
    mm = MemoryManager()
    artifact = mm.read_artifact(tx_hash)
    assert artifact["receipt_type"] == "LLMContext"
    ctx = artifact["payload"]
    print(f"[1/4] LLMContext fetched. Model: {ctx['model_id']}, T: {ctx['temperature']}")

    # Reconstruct messages
    client = OpenAI()
    response = client.chat.completions.create(
        model=ctx["model_id"].split("/", 1)[-1],
        messages=[{"role":"system","content":ctx["system_prompt"]}] + ctx["messages"],
        temperature=ctx["temperature"],
        seed=ctx.get("seed"),
    )
    raw = response.choices[0].message.content
    print(f"[2/4] Replayed response: {raw[:80]}...")

    # Compare hashes (parsed)
    # For structured outputs, the parsed_hash compares to the JSON of parsed obj
    # Simpler check here: compare raw response hash with original
    original_raw_hash = "0x" + keccak(ctx["response_raw"].encode()).hex()
    replay_raw_hash   = "0x" + keccak(raw.encode()).hex()
    print(f"[3/4] Original raw hash: {original_raw_hash[:14]}...")
    print(f"[4/4] Replay  raw hash : {replay_raw_hash[:14]}...")
    if original_raw_hash == replay_raw_hash:
        print("✓ DETERMINISTIC MATCH — decision is verifiable")
    else:
        print("⚠ raw response differs (expected with high temperature; structured-output schema_hash still binds intent)")
        print(f"  schema_hash: {ctx['structured_output_schema_hash']}")
        print(f"  parsed_hash: {ctx['response_parsed_hash']}")
```

> Note on determinism: at `temperature=0.0` with a seed, OpenAI is *largely* deterministic but not byte-stable. We solve this by also storing `response_parsed_hash` over the *parsed* structured output — schema-bounded objects are far more reproducible than raw strings. The script reports both.

### [x] Step 6.5 — Verifier walks the chain
**File:** `verify_audit.py`

```python
def walk_chain(self, head_hash: str | None = None) -> bool:
    head = head_hash or AuditChainHead().head
    cur, count = head, 0
    while cur:
        receipt = self._fetch_0g_receipt(cur)
        if not self._integrity_ok(receipt):  return False
        if receipt["receipt_type"] in ("DecisionReceipt","ExecutionReceipt"):
            if not self._verify_signatures(receipt): return False
        if receipt["receipt_type"] == "AttackRejection":
            print(f"  ⚠ ATTACK_REJECTED [{receipt['payload']['attack_kind']}] — defended by {receipt['payload']['detected_by']}")
        cur = receipt.get("prev_0g_tx_hash")
        count += 1
    print(f"CHAIN VERIFIED — {count} receipts walked.")
    return True
```

### [x] Step 6.6 — Reorg awareness
`MIN_CONFIRMATIONS = 3`. Verifier polls until receipt has ≥3 confirmations before declaring `CONFIRMED`.

### [x] Step 6.7 — **ArbiterReceipt SBT (elite-5a)**
**New file:** `contracts/ArbiterReceipt.sol` (per `SYSTEM_DESIGN §13.1`).

**Foundry deployment:**
```bash
forge script script/DeployArbiterReceipt.s.sol \
    --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_KEY --broadcast --verify
echo "ARBITER_RECEIPT_NFT=0x..." >> .env
```

**Wire into Execution Node:** after `dedupe.mark(...)`, call:
```python
nft = w3.eth.contract(address=ARBITER_RECEIPT_NFT, abi=ARBITER_RECEIPT_ABI)
zero_g_uri = f"0g://{decision_receipt_tx_hash}"
mint_tx = nft.functions.mintReceipt(receipt_hash_bytes32, zero_g_uri).build_transaction({...})
# sign with EXECUTOR_KEY, send
```

**Acceptance:**
* `verify_audit.py` walks ≥10 receipts and prints `CHAIN VERIFIED`.
* `replay_decision.py` shows `parsed_hash` match for at least one past LLM call.
* Sepolia shows the Safe holding ≥1 `ARDR` NFT; clicking the tokenURI resolves to a 0G receipt.

---

## 9. Day 8 — MVP 7.0: Resilience + Byzantine Watchdog ✱ Elite-4 + Chaos

**Objective:** Survive the chaos matrix. **Demonstrate adversarial resilience on camera via the Byzantine Watchdog.**

### [x] Step 7.1 — Heartbeats + reconnection backoff
* `core/retry.py` — exponential backoff with jitter.
* `Heartbeat` published every 5s by every daemon.
* Patriarch silence > 30s ⇒ Quant marks proposal `EXPIRED`.
* `state/pending_0g.jsonl` — retry queue for 0G writes during RPC outage.

### [x] Step 7.2 — **Byzantine Watchdog (elite-4)**
**New file:** `byzantine_watchdog.py`

```python
"""
DEMO-ONLY 5th process. Publishes a scripted sequence of attacks on the AXL bus.
The system is expected to reject every one. Each rejection is forensically recorded on 0G.

Run AFTER the legitimate scenario completes (so the watchdog sees a real proposal in flight
or replays a known-stale one).

Usage:
  python byzantine_watchdog.py --attack A1
  python byzantine_watchdog.py --attack-sequence  # all six in order, 4s apart
"""
import argparse, time, copy, json, os
from core.network import MockAXLNode
from core.models import Proposal, ConsensusMessage, SimulationResult
from core.crypto import sign_digest
from eth_account import Account

ATTACKER_KEY = bytes.fromhex(os.getenv("ATTACKER_PRIVATE_KEY")[2:])
ATTACKER_ADDR = Account.from_key(ATTACKER_KEY).address
node = MockAXLNode("Adversary_Node_Z")

def attack_A1_invalid_sig(real_proposal: Proposal):
    bad = real_proposal.model_copy(deep=True)
    bad.proposal_id = real_proposal.proposal_id + "_attk_A1"
    # Sign with the attacker's key (not a Safe owner)
    bad.quant_signature = "0x" + "00"*65 + "00"*65
    node.publish("PROPOSALS", bad.model_dump())
    print("[A1] Published malformed proposal with garbage signature.")

def attack_A2_replay_nonce(executed_proposal_id: str):
    # Re-publish a CONSENSUS_SIGNATURES from an already-executed proposal
    fake = ConsensusMessage(
        proposal_id=executed_proposal_id, iteration=1,
        signer_id="Adversary_Node_Z", signer_address=ATTACKER_ADDR, role="approver",
        safe_tx_hash="0x"+"22"*32, signature="0x"+"00"*65, timestamp=time.time(),
    )
    node.publish("CONSENSUS_SIGNATURES", fake.model_dump())
    print("[A2] Replayed nonce.")

def attack_A3_math_forge(real_proposal: Proposal):
    forged = real_proposal.model_copy(deep=True)
    forged.proposal_id += "_attk_A3"
    forged.risk_score_bps = 100   # way under the real risk
    # Don't update quant_analysis_hash — keep the stale one
    node.publish("PROPOSALS", forged.model_dump())
    print("[A3] Forged math, kept stale analysis hash.")

def attack_A4_whitelist_bypass(real_proposal: Proposal):
    bad = real_proposal.model_copy(deep=True)
    bad.proposal_id += "_attk_A4"
    bad.asset_in = "DOGE"
    node.publish("PROPOSALS", bad.model_dump())
    print("[A4] Non-whitelisted asset.")

def attack_A5_fake_sim_result(real_proposal: Proposal):
    fake = SimulationResult(
        request_id="forged", proposal_id=real_proposal.proposal_id, success=True,
        gas_used=100000, return_data="0x", revert_reason=None, fork_block=0,
        simulator_signature="0x"+"00"*65, timestamp=time.time(),
    )
    node.publish("SIM_ORACLE_RESULT", fake.model_dump())
    print("[A5] Unsigned/forged sim result.")

def attack_A6_wrong_domain(real_proposal: Proposal):
    bad = real_proposal.model_copy(deep=True)
    bad.proposal_id += "_attk_A6"
    bad.chain_id = 1   # mainnet — Patriarch's recompute of proposal_hash will diverge
    node.publish("PROPOSALS", bad.model_dump())
    print("[A6] Wrong chain id in EIP-712 domain.")
```

**Watchdog evidence panel:** `monitor_network.py` adds a red "ATTACK_REJECTED" sub-pane that subscribes to the `ATTACK_REJECTED` AXL topic and renders the attack id + kind + defender in real time.

**Forensic 0G writes:** every defender (Patriarch, Execution Node) calls `publish_attack_rejection(attack_id, kind, evidence)` which writes an `AttackRejection` receipt to 0G **and** publishes to AXL.

### [x] Step 7.3 — Chaos test scripts
**New directory:** `scripts/chaos/`

| Script | Asserts |
|---|---|
| `kill_patriarch_mid_negotiation.sh` | Quant times out at 30s, RejectionReceipt written |
| `kill_executor_after_one_sig.sh` | Restart, 2-of-2 completes once, no double-execute |
| `simulate_0g_outage.sh` | Receipts queue then drain on restoration |
| `gas_spike_500gwei.sh` | Firewall rejects, EXECUTION_FAILURE recorded |
| `keeperhub_mcp_crash.sh` | Patriarch sim-oracle times out at 8s, OUTSIDE_MANDATE reject |
| `byzantine_full_sequence.sh` | All 6 attacks rejected, all 6 forensic receipts on 0G |

**Acceptance (go/no-go):** All 6 chaos scripts pass back-to-back. CI logs committed. Watchdog evidence pane on monitor flashes red 6 times in 24 seconds.

---

## 10. Day 9 — MVP 7.1: Demo Polish + Public Verifier + QR ✱ Elite-5b

**Objective:** Lock the demo recording flow. Audience-verifiable.

### [x] Step 8.1 — Multi-pane "God View" monitor
**File:** `monitor/monitor_network.py`

`rich.layout.Layout` with four columns:
1. **AXL Stream** (existing).
2. **Treasury State**: Safe balances per asset, daily drawdown vs cap, `nonce`, last 3 SBT mints with tokenURI links.
3. **Audit Chain Tail**: last 5 0G receipts with `tx_hash`, `prev_0g_tx_hash`, signature recovery results.
4. **Watchdog Evidence**: red-flash list of `ATTACK_REJECTED` events with kind + defender.

### [x] Step 8.2 — Public verifier page (elite-5b)
**New directory:** `monitor/public_verifier/`

Static site (Next.js or plain HTML+JS) deployed to Vercel:
* `index.html` — pulls audit chain head from `/api/head` (which proxies a public 0G RPC call to read `audit_chain_head.json` from a known IPFS pin OR directly from the latest 0G tx by the executor).
* Walks the chain, signature-verifies in browser (ethers.js), renders a tree of receipts.
* Per-receipt panel: signature recovery, USD value (decimals-correct), Sepolia tx link, SBT link, LLMContext link.
* Big green badge: `CHAIN VERIFIED ✓ N receipts` or red `INTEGRITY FAIL`.

The Monitor pane #2 renders a QR linking to this page.

**Recording-day rehearsal:** Day 9 dress rehearsal includes recording someone scanning the QR with their phone and seeing the same `CHAIN VERIFIED` state.

### [x] Step 8.3 — Demo orchestration script
**New file:** `scripts/demo_run.py`

```python
"""
Drives the recording in one command. No undetermined outcome — every wait step
asserts an expected event arrives within timeout, otherwise aborts.

Usage:
  python scripts/demo_run.py
  python scripts/demo_run.py --record demo.mp4 --skip-watchdog
"""
import subprocess, time, asyncio
from core.network import MockAXLNode

STEPS = [
    ("inject", "flash_crash_eth", "EXECUTION_SUCCESS", 60),
    ("inject", "pendle_yield_arbitrage", "EXECUTION_SUCCESS", 90),  # 2 iterations
    ("watchdog", "A1..A6", "ATTACK_REJECTED x 6", 30),
    ("inject", "protocol_hack", "EXECUTION_SUCCESS", 30),
    ("inject", "gas_war", "PROPOSAL_NONE_GENERATED", 20),
    ("replay", "<latest_proposal_id>", "DETERMINISTIC_MATCH or PARSED_MATCH", 30),
    ("verify", "walk-from-head", "CHAIN VERIFIED >= 12 receipts", 30),
]
```

The script blocks at each step until either the assertion fires or the timeout expires. Timeout aborts with a clear error.

### [x] Step 8.4 — `docs/KEEPERHUB_FEEDBACK.md` ✱ compliance-8 (Builder Feedback Bounty $250)

KeeperHub's Builder Feedback bounty pays $250 for "specific, actionable feedback on UX friction, reproducible bugs, or documentation gaps encountered while using KeeperHub during the event." Up to two teams win. We've used KeeperHub all week — by Day 9 we'll have accumulated friction points. **This is the cheapest $250 in the prize pool**; do not skip it.

**New file:** `docs/KEEPERHUB_FEEDBACK.md`

Template — fill in actual entries from our experience:

```markdown
# KeeperHub Builder Feedback — Arbiter Capital

**Submitted:** 2026-05-05
**Project:** Arbiter Capital (ETHGlobal Open Agents)
**Repo:** https://github.com/...
**Total integration time:** ~3 days (Days 5–7 of our sprint)
**Build context:** Multi-agent DeFi treasury manager using KeeperHub as both Safe Module executor AND a Sim Oracle in agent consensus.

## Friction Point #1: <short title>
**Date encountered:** 2026-04-...
**Affected component:** <MCP / SDK / Module install / etc.>
**Reproduction:**
1. <exact command>
2. <exact command>
**Expected:** <one sentence>
**Actual:** <one sentence + log excerpt>
**Workaround:** <if any>
**Suggested fix:** <one sentence>

## Friction Point #2: ...

## Documentation Gap #1: ...
**Page URL:** <link>
**What was missing:** <one sentence>
**What we had to figure out:** <one sentence>
**Suggested doc addition:** <draft paragraph>

## Positive notes (what worked unusually well)
- ...

## Asks for v-next
- ...
```

**Workflow:**
1. Throughout Days 5–7, every team member who hits KeeperHub friction logs a one-liner in `docs/KEEPERHUB_FEEDBACK.scratch.md`.
2. Day 9 morning, edit `KEEPERHUB_FEEDBACK.md` to formal entries (≥3 friction points + ≥1 doc gap).
3. Submit URL via the dedicated bounty form (KeeperHub typically provides a Typeform — check Day 9 morning).

**Acceptance:** File exists, ≥3 friction-point H2 sections, each has Date / Repro / Expected / Actual fields. CI gate `scripts/check_bounty_compliance.py` enforces this.

### [ ] Step 8.5 — Dress rehearsal
Run `scripts/demo_run.py` end-to-end three times in a row with fresh `state/`. All three must pass. Record once with OBS; this is the insurance recording.

**Acceptance:**
* `scripts/demo_run.py` completes in 4-5 minutes on Sepolia, three runs in a row.
* Watchdog rejection pane flashes red 6 times during the recording.
* QR scan resolves to the same `CHAIN VERIFIED` state on a separate device.
* `replay_decision.py` shows `parsed_hash` match for at least one LLM call.
* `bash scripts/check_bounty_compliance.py` exits 0 on the dress-rehearsal run.

---

## 11. Day 10 — Submission

### [ ] Step 9.0 — `scripts/check_bounty_compliance.py` (auto-enforced gate)

**New file** — runs before submission. Refuses to ship if any bounty hard requirement (per `SYSTEM_DESIGN §2.5`) fails.

```python
#!/usr/bin/env python
"""Bounty compliance gate. Exit 0 = ship-ready. Non-zero = fix before submitting."""
import os, sys, sqlite3, json, subprocess
from pathlib import Path
from langchain_core.tools import BaseTool

FAIL = []
OK   = []

def check(name, condition, detail=""):
    (OK if condition else FAIL).append(f"{name} {'✓' if condition else '✗'} {detail}")

# Gensyn HR(a): live AXL only on demo path
from core.network import MockAXLNode
n = MockAXLNode("compliance_check", url_env="AXL_NODE_URL_QUANT")
check("gensyn.live_axl", n.use_live_axl, f"axl_url={n.axl_url}")

# Gensyn HR(b): cross-node communication
import sqlite3
with sqlite3.connect("axl_network.db") as c:
    senders = {r[0] for r in c.execute("SELECT DISTINCT sender FROM messages WHERE timestamp > ?",
                                        (__import__('time').time() - 3600,))}
check("gensyn.cross_node", len(senders) >= 4, f"distinct senders last 1h: {sorted(senders)}")

# KeeperHub F1: sim oracle invoked
with sqlite3.connect("axl_network.db") as c:
    sim_count = c.execute("SELECT COUNT(*) FROM messages WHERE topic='SIM_ORACLE_REQUEST'").fetchone()[0]
check("keeperhub.f1_sim_oracle", sim_count >= 3, f"invocations: {sim_count}")

# KeeperHub F2: LangChain bridge
try:
    from langchain_keeperhub import KeeperHubSimulateTool, KeeperHubExecuteTool
    check("keeperhub.f2_langchain_bridge",
          isinstance(KeeperHubSimulateTool(), BaseTool) and isinstance(KeeperHubExecuteTool(), BaseTool))
except ImportError as e:
    check("keeperhub.f2_langchain_bridge", False, f"import failed: {e}")

# KeeperHub Builder Feedback
fb = Path("docs/KEEPERHUB_FEEDBACK.md")
if fb.exists():
    txt = fb.read_text()
    check("keeperhub.builder_feedback",
          fb.stat().st_size >= 4096 and txt.count("\n## ") >= 3,
          f"size={fb.stat().st_size}, h2_count={txt.count(chr(10)+'## ')}")
else:
    check("keeperhub.builder_feedback", False, "file missing")

# Uniswap T3: hook deployed and verified
hook = os.getenv("ARBITER_THROTTLE_HOOK", "")
check("uniswap.hook_deployed", hook.startswith("0x") and len(hook) == 42, f"address={hook}")

# 0G T3: LLMContexts on-chain
import sqlite3
# (replace with real 0G read in v5.1+; here we count local cache)
zerog = Path("0g_storage")
ctxs = list(zerog.glob("*.json")) if zerog.exists() else []
ctx_count = sum(1 for f in ctxs if 'LLMContext' in f.read_text()[:500])
check("zerog.llm_contexts", ctx_count >= 6, f"count: {ctx_count}")

# 0G T3: hash-chain walk
result = subprocess.run([sys.executable, "verify_audit.py", "--walk-from-head"],
                       capture_output=True, text=True)
check("zerog.chain_walk", "CHAIN VERIFIED" in result.stdout, result.stdout[-200:])

print("\n=== BOUNTY COMPLIANCE ===")
for o in OK:   print("  " + o)
for f in FAIL: print("  " + f)
print(f"\n{len(OK)}/{len(OK)+len(FAIL)} checks passed.")
sys.exit(1 if FAIL else 0)
```

Run: `python scripts/check_bounty_compliance.py`. Day 10 cannot proceed unless this prints all green.

### [ ] Step 9.1 — Final documentation
* `README.md` — replace MVP 6 claims with v5.1 reality. Add architecture diagram (export from `SYSTEM_DESIGN §3.1`). Link to public verifier.
* `GEMINI.md` — update.
* `docs/SECURITY.md` — copy threat model, add disclaimers.
* `docs/AUDIT_REPRODUCE.md` — step-by-step "anyone can replay our audit chain."
* `docs/KEEPERHUB_FEEDBACK.md` — already finalized in Step 8.4.
* `docs/BOUNTY_PROOF.md` — explicit bounty-by-bounty submission proof, ordered by prize size:
  * **0G ($15k):** N×`LLMContext` tx hashes (≥6), N×`DecisionReceipt` tx hashes (≥3), `replay_decision.py` output showing parsed_hash match, audit chain length, link to public verifier.
  * **Gensyn ($5k):** AXL deployment instructions, 5 distinct AXL node IDs visible on monitor, watchdog forensic log (≥6 `AttackRejection` receipts on 0G), `core/network.py::_assert_demo_transport` enforcement code.
  * **Uniswap ($5k):** `ArbiterThrottleHook` deployment tx + verified contract on Etherscan + ≥1 swap routed through it (with PoolKey containing the hook address, visible in event log).
  * **KeeperHub Best Use ($4.5k, hitting BOTH focus areas):** Module-enable tx, sim oracle invocations (≥3), MCP tool list, `langchain_keeperhub.py` source link, F2 evidence.
  * **KeeperHub Builder Feedback ($500):** `docs/KEEPERHUB_FEEDBACK.md` URL, submission timestamp.
  * **Grand Prize / "AI agents that live onchain":** narrative summary tying all of the above together — 4 onchain-bound personas, signed agent-to-agent negotiation, autonomous Safe execution, reproducible AI memory.

### [ ] Step 9.2 — Final smoke test
`scripts/demo_run.py` three times in a row. All must pass. Insurance recording archived.

### [ ] Step 9.3 — Recording & submission
* Record 3 minutes via OBS following the storyboard in `SYSTEM_DESIGN §17`.
* Upload to ETHGlobal portal.
* Submit:
  * GitHub repo URL.
  * Demo video URL.
  * Safe address.
  * Public verifier URL.
  * List of 0G receipt tx hashes (incl. ≥6 LLMContext, ≥6 AttackRejection, ≥3 ExecutionReceipt).
  * List of Sepolia execution tx hashes.
  * `ArbiterThrottleHook` deployment + verification link.
  * `ArbiterReceipt` SBT contract + ≥3 minted token URIs.

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|:-:|:-:|---|
| UR Sepolia address moves | Low | High | Pin Day 5 morning; re-verify Day 9 morning |
| 0G testnet outage during recording | Medium | High | Insurance recording from Day 9; `EMBEDDINGS_LOCAL=1` fallback |
| KeeperHub MCP unstable | Medium | High | Direct Safe broadcast fallback in `treasury.execute_with_signatures`; KeeperHub bounty still claimable via Module-enable + Sim Oracle invocations alone |
| Patriarch LLM no-converge | Low | Medium | Iter cap = 3 ⇒ EXPIRED; demo scenarios pre-tuned |
| Key compromise during prep | Low | High | Generate fresh keys Day 1; rotate post-demo |
| Permit2 approvals not finalized | Medium | High | Day 6 includes one-time `enable_permit2.py` |
| Sepolia RPC rate-limited | Medium | Medium | Round-robin Alchemy + Ankr in `core/retry.py` |
| EIP-712 hash mismatch Python vs Safe | Medium | High | Day 2 acceptance: byte-equal vs `safe.build_multisig_tx().safe_tx_hash` for 5 calldatas |
| ArbiterThrottleHook deployment fails | Medium | High | Foundry test harness Day 5 morning; `HookMiner` salt mining can take ≥10 min — start early |
| Watchdog crashes the legit pipeline | Low | High | Watchdog is a *separate process*; defender publishes `ATTACK_REJECTED` rather than crashing; fault-isolated |
| QR/public verifier page slow on demo wifi | Medium | Medium | Pre-rendered fallback screenshot + cached JSON |

---

## 13. Acceptance Criteria for Submission

All must be **true and demonstrable**:

1. ☐ `pytest tests/` ≥12 collected, ≥12 passing.
2. ☐ `python verify_audit.py --walk-from-head` → `CHAIN VERIFIED ≥ 12 receipts`.
3. ☐ Sepolia explorer shows ≥3 swaps from the project Safe via UR through the Sepolia v4 PoolManager.
4. ☐ At least one swap routes through `ArbiterThrottleHook` (visible in the swap event hook field).
5. ☐ `ARBITER_THROTTLE_HOOK` and `ARBITER_RECEIPT_NFT` are verified contracts on Sepolia Etherscan.
6. ☐ Both `QUANT_ADDR` and `PATRIARCH_ADDR` are Safe owners (threshold = 2). KeeperHub address is enabled as a Safe Module.
7. ☐ Signature recovery on `EXECUTION_SUCCESS` receipts returns exactly `{QUANT_ADDR, PATRIARCH_ADDR}`.
8. ☐ ≥6 `LLMContext` receipts on 0G; `replay_decision.py` succeeds on at least one with `parsed_hash` match.
9. ☐ ≥6 `AttackRejection` receipts on 0G (one per Watchdog attack class).
10. ☐ ≥3 `ArbiterReceipt` SBTs minted to the Safe.
11. ☐ All 6 chaos scripts pass.
12. ☐ `scripts/demo_run.py` completes 3-times-in-a-row without manual intervention.
13. ☐ Public verifier page shows live `CHAIN VERIFIED` on a separate device via QR scan.
14. ☐ ETHGlobal portal submission complete with `BOUNTY_PROOF.md` artifacts.
15. ☐ **Live AXL nodes ≥4 distinct** running for the demo recording; `core/network.py::_assert_demo_transport` enforced; ≥4 distinct `sender` values in `monitor_network.py`'s last-60s window. (Gensyn HR.)
16. ☐ **`langchain_keeperhub.py` exists and is importable**; `isinstance(KeeperHubSimulateTool(), BaseTool)` is True. (KeeperHub F2.)
17. ☐ **`docs/KEEPERHUB_FEEDBACK.md` filed** with ≥3 friction-point sections (≥4 KB). (KeeperHub Builder Feedback.)
18. ☐ **`scripts/check_bounty_compliance.py` exits 0** before submission.

---

## 14. Post-Hackathon (v6 backlog, NOT in scope)

* Threshold-ECDSA / FROST.
* Patriarch ensemble (3-of-3 distinct LLM providers).
* Real-time Chainlink oracle in firewall.
* Cross-chain treasury via LayerZero / Wormhole.
* MEV protection via Flashbots Protect / private mempool.
* DAO-governed firewall constants.
* Halmos / Certora formal verification of firewall + ArbiterThrottleHook.
* Slashing economics (bonded agent stakes).
* Quant model upgrade: learned policy (transformer regime classifier) gated behind backtesting.
* Fully on-chain LLMContext storage proof via 0G's data-availability sampling.

---

*End of TECHNICAL_ROADMAP.md v5.0 ("Winning Sprint"). Cross-reference: `SYSTEM_DESIGN.md v5.0` for the canonical architectural specification. Living documents — update at the end of each MVP day.*
