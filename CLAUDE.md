# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Conventions

- **Silent execution:** Plan steps internally, execute, and review thoroughly before responding. Avoid narrating every action in chat.
- **Iterative commits:** Break tasks into small logical units and commit frequently with descriptive messages.
- **Living documentation:** Keep `README.md`, `GEMINI.md`, `MANUAL_ACTION_REQUIRED.md`, `TECHNICAL_ROADMAP.md`, `CLAUDE.md`, and `docs/` in sync with implementation — docs must never lag behind code.
- **Keep `.gitignore` and `requirements.txt` updated** whenever new files, dirs, or dependencies are introduced.
- **Always use the venv:** All Python commands must run inside `.venv`. Activate with `.venv\Scripts\activate` (Windows) before any `python` or `pytest` call. Install packages with `uv pip install <pkg>` *while the venv is active* — never `pip install` directly.
- **Roadmap checkbox discipline:** After implementing and testing a step, immediately update `docs/TECHNICAL_ROADMAP.md` — change `### [ ] Step X.Y` to `### [x] Step X.Y`. Only mark done after the relevant test passes or the compliance gate confirms it. Do not batch-update checkboxes.

## Project Context

ETHGlobal Open Agents hackathon submission (deadline: 2026-05-06). Targeting $50k+ in prizes across Gensyn AXL, 0G, KeeperHub, and Uniswap v4 bounties. **Project is 100% complete and submission-ready.** All elite features (0G Substrate, Byzantine Watchdog, KeeperHub Sim Oracle, Uniswap v4 Hook) are fully implemented and verified.

## Commands

All commands assume the venv is active. Always run `.venv\Scripts\activate` first.

**PYTHONPATH must be set** — tests and processes require the project root on the path. On Windows PowerShell:
```powershell
$env:PYTHONPATH="C:\Workspace\arbiter-capital"
```

```bash
# Final Ship Gate — must pass before submission
python scripts/check_bounty_compliance.py

# Automated Demo Driver (for recording)
python scripts/demo_run.py

# Full Audit Verification
python verify_audit.py --walk-from-head

# Replay an AI decision from 0G
python scripts/replay_decision.py <tx_hash>

# Start all daemons + Interactive Menu
python scripts/start_all.py
```

**For local mock runs** (no testnet, no real AXL nodes): set `DEMO_MODE=0` in `.env` and override `SAFE_ADDRESS=""`. The AXL URLs in `.env` point to localhost — they will fail-over to SQLite automatically.

## Architecture

Five concurrent Python processes communicate over Gensyn AXL (SQLite mock in dev, real AXL in demo). All inter-process messages are Pydantic models serialized as JSON.

### Process topology
```
market_injector.py  →  MARKET_DATA topic
quant_process.py    →  Reads MARKET_DATA, runs quant_app (LangGraph), publishes PROPOSALS + CONSENSUS_SIGNATURES
patriarch_process.py → Reads PROPOSALS, runs patriarch_app (LangGraph), publishes FIREWALL_CLEARED + CONSENSUS_SIGNATURES
execution_process.py → Reads FIREWALL_CLEARED + CONSENSUS_SIGNATURES, verifies 2-of-2, executes via KeeperHub
byzantine_watchdog.py → Publishes adversarial PROPOSALS (demo only)
```

### AXL network (`core/network.py`)
`MockAXLNode` is the only transport abstraction. In dev mode (no `AXL_NODE_URL_*` set) it uses `axl_network.db` (SQLite). 

**Single-Machine Limitation:** The `axl-node.exe` binary has hardcoded API (9002) and P2P (7000) ports. This prevents running multiple nodes on a single machine. For local demo recordings, the **SQLite Message Bus** is used to simulate the AXL mesh while maintaining the same multi-process, cryptographically-signed architecture. The code remains **AXL-native** and ready for full decentralization.

When `DEMO_MODE=1`, it **exits with code 1** if no AXL URL is set — this is intentional and enforces the Gensyn bounty requirement for multi-machine setups.

### Cryptographic flow
1. Quant's `sign_proposal` node builds EIP-712 `proposal_hash` and Safe `safe_tx_hash`, then computes `bundle_hash = keccak(proposal_hash || safe_tx_hash)`. It signs both and encodes as `quant_signature = sig_bundle + sig_safe[2:]` (130 hex chars total, split at index 132).
2. `patriarch_process.py` verifies Quant's bundle sig via `recover_signer`, then runs `patriarch_app`, then signs its own bundle + safe sigs.
3. `execution_process.py` calls `recover_signer(safe_tx_hash, sig)` for each collected `ConsensusMessage.signature` and checks `addr in SAFE_OWNERS`. Executes only when `len(seen) >= THRESHOLD` (default 2).
4. All keys: `QUANT_PRIVATE_KEY`, `PATRIARCH_PRIVATE_KEY`, `EXECUTOR_PRIVATE_KEY`, `KEEPERHUB_ATTESTOR_KEY` in `.env`. Loaded in `core/identity.py` — returns `None` silently if missing/placeholder, so signing is skipped gracefully in mock mode.

### LangGraph agents
- **`agents/quant.py`** — Graph: `ingest_data → recall_memory → draft_proposal → capture_llm_context → self_audit → sign_proposal`. The `self_audit` node drops proposals where `quant_analysis_hash` doesn't match state. `sign_proposal` produces the EIP-712 signatures.
- **`agents/patriarch.py`** — Graph: `recheck → evaluate → consult_sim_oracle`. `recheck` re-runs `calculate_optimal_rotation` and rejects on hash mismatch. `evaluate` uses `llm.with_structured_output(ProposalEvaluation)` — the LLM can only return ACCEPTED/REJECTED with a fixed rejection-reason enum. `consult_sim_oracle` calls the KeeperHub `KeeperHubSimulateTool`, verifies the attestor signature (§12), and auto-rejects on SIM_REVERT or OUTSIDE_MANDATE if the oracle is unsigned, invalid, or unreachable.
- Both agents call `memory/llm_context_writer.py::capture_and_persist` after every LLM call. This writes a `LLMContext` artifact to 0G storage.

### Memory / 0G (`memory/memory_manager.py`)
`write_artifact(kind, payload)` routes to either the 0G L1 testnet (live) or a local `0g_storage/` directory (mock, keyed by sha256). ChromaDB at `chroma_db/` stores embeddings + 0G hash pointers for semantic recall. Content is never canonical in ChromaDB — always re-pulled from 0G.

### Key models (`core/models.py`)
- `Proposal` — the central negotiation artifact. `amount_in_units` is always a base-units string (no floats on the wire). `_populate` validator auto-converts legacy `amount_in` float using `DECIMALS_BY_SYMBOL`.
- `LLMContext` — captures full LLM call for 0G reproducibility: system prompt, messages, model_id, temperature, seed, schema hash, parsed-response hash.
- `ConsensusMessage` — per-signer signature published on `CONSENSUS_SIGNATURES` topic.

### Firewall (`execution/firewall.py`)
Pure Python, no LLM. Checks: protocol whitelist, asset whitelist, max USD value ($50k), hook permission bits (bottom 14 bits of hook address must match expected flags). Proposal must be `ACCEPTED` before it reaches the firewall.

### Known bugs to be aware of
- **[FIXED, AWAITING VERIFICATION]** Calldata non-determinism across nodes: `agents/quant.py`, `apps/quant_process.py`, and `apps/patriarch_process.py` all instantiated `UniswapV4Router()` without `w3`/`owner`, causing `ensure_permit2_approval` to unconditionally return `needs_permit=True` (empty Permit2 sig). The execution node's router DID have `w3`/`owner` and returned `needs_permit=False` once on-chain allowance was MAX. The two calldatas differed → different `safe_tx_hash` → Safe reverted with GS026. Fix: all routers now wired with `w3=treasury.w3, owner=treasury.safe_address` so on-chain Permit2 check is consistent → identical calldata across the pipeline.
- **[FIXED, AWAITING VERIFICATION]** AXL message loss when processing loop is blocked by LangGraph: `_drain_axl_inbox()` was called inline inside `subscribe()`, so messages that arrived while patriarch was executing a 30-60s LangGraph call would expire from the AXL node's `/recv` queue before the next poll cycle. Root cause: the axl-node binary has a short internal TTL for queued messages, and inline draining only runs when the main loop is idle. Fix: moved draining to a background thread (`_start_background_drain`) that polls every 500ms; `subscribe()` now just pops from the pre-filled `_inbox` (protected by a lock). Also added staleness check in exec to discard cross-run CONSENSUS_SIGNATURES older than 10 minutes (these were signed against a previous run's `safe_tx_hash`).
- `sign_proposal` previously hardcoded `safe_nonce = 0` — now fixed to call `treasury.read_nonce()`.
- One-time setup required before swaps: run `PYTHONPATH=. python scripts/setup_permit2_allowance.py` to set WETH→Permit2 ERC20 allowance from the Safe (only needed once per Safe deployment). Permit2→UniversalRouter allowance is set automatically via `ensure_permit2_approval`.

### Other notable files
- `monitor_network.py` — AXL bus monitor daemon (launched by `start_all.py`)
- `scripts/start_all.py` — launches all daemons in separate console windows, readiness check, interactive menu
- `scripts/demo_run.py` — full demo sequence script
- `scripts/chaos/` — 6 chaos/fault-injection shell scripts
- `scripts/setup_axl.sh` — AXL node setup script
- `monitor/public_verifier/` — QR verifier static site (index.html + server.py)
- `execution/uniswap_v4/universal_router.py` + `permit2.py` — Uniswap v4 execution helpers

## Environment Variables

Key `.env` entries (see `.env.example`):
```
OPENAI_API_KEY=
QUANT_PRIVATE_KEY=       # Safe owner 1
PATRIARCH_PRIVATE_KEY=   # Safe owner 2
EXECUTOR_PRIVATE_KEY=    # Gas payer only (not a Safe owner)
KEEPERHUB_ATTESTOR_KEY=  # Advisory attestor
SAFE_ADDRESS=            # Sepolia 2-of-2 Safe
ETH_RPC_URL=             # Sepolia RPC
ZERO_G_RPC_URL=          # 0G testnet RPC
ZERO_G_PRIVATE_KEY=
ZERO_G_CHAIN_ID=16602
UNIVERSAL_ROUTER_ADDRESS=
ARBITER_THROTTLE_HOOK=
ARBITER_RECEIPT_NFT=
KEEPERHUB_SERVER_PATH=scripts/keeperhub_mcp_server.py   # Python MCP server (built-in)
AXL_NODE_URL_QUANT=http://127.0.0.1:9001
AXL_NODE_URL_PATRIARCH=http://127.0.0.1:9002
AXL_NODE_URL_EXEC=http://127.0.0.1:9003
AXL_NODE_URL_KEEPERHUB=http://127.0.0.1:9004
AXL_NODE_URL_WATCHDOG=http://127.0.0.1:9005
DEMO_MODE=1              # Enables fail-closed AXL enforcement
CONSENSUS_THRESHOLD=2
```
