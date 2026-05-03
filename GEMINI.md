# Arbiter Capital — Autonomous Family Office (v5.0 — "Winning Edition")

## Project Overview

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across DeFi while solving the "black box" trust issue. The system splits AI cognition into four isolated personas—an aggressive **Yield Quant**, a conservative **Risk Patriarch**, a **Sim-Oracle Auditor (KeeperHub)**, and a **Byzantine Watchdog**—that debate and reach consensus over a decentralized **Gensyn AXL** P2P mesh.

Trades are only executed via a **2-of-2 treasury Safe** when cryptographically verifiable consensus (EIP-712) is reached. Every decision, transcript, and full LLM context is hash-chained to the **0G Layer 1** as the canonical AI memory substrate.

**Key Technologies & Architecture:**
*   **Agent Framework:** Python-based LangGraph.
*   **LLM:** OpenAI GPT-4o (Decision making).
*   **Networking:** Gensyn AXL for decentralized P2P agent communication (No centralized brokers).
*   **Execution & Custody:** KeeperHub (Safe Module & MCP) integrated with a Safe (Smart Account) for deterministic execution.
*   **DeFi Target:** Uniswap v4 (ArbiterThrottleHook), Lido (LSTs), and Pendle (Yield Trading).
*   **Immutable Memory:** 0G Layer 1 for hash-chained audit trails and reproducible LLM contexts.

## Project Roadmap (v5.0 "Winning Sprint")

The detailed implementation plan is tracked in [docs/TECHNICAL_ROADMAP.md](docs/TECHNICAL_ROADMAP.md).

*   **MVP 6 (COMPLETED):** **Winning Edition Hardening.** EIP-712, true 2-of-2 signatures, 0G LLM Substrate, and ArbiterThrottleHook.
*   **MVP 7 (COMPLETED):** Byzantine Watchdog, Chaos testing, and Public Verifier UI.

## Running the Network

The architecture requires five separate processes to prove decentralization. Due to hardcoded port conflicts in the `axl-node.exe` binary (9002/7000), a local mesh on a single machine is simulated via a shared SQLite bus.

1.  **Local Demo Path (Recommended):**
    *   Set `DEMO_MODE=0` in `.env`.
    *   Run `$env:PYTHONPATH="."; python scripts/start_all.py`.
    *   Inject scenarios via the interactive menu.

2.  **Full AXL P2P Path:**
    *   Requires nodes on separate machines/containers.
    *   Set `DEMO_MODE=1` in `.env`.
    *   Configure `AXL_NODE_URL_*` and `AXL_NODE_KEY_*` in `.env`.
    *   Run `python scripts/start_all.py`.

## Development Conventions

*   **Cognitive Isolation:** No single process holds both yield and risk authority. All agent communication MUST happen over the AXL network following the `Proposal` JSON schema.
*   **Cryptographic Accountability:** All agreements must be EIP-712 signed artifacts. Signatures MUST be verified before processing any payload.
*   **Reproducible AI Memory:** Every LLM call MUST have its full context (system prompt, messages, model, temperature, schema hash) persisted to 0G. The `replay_decision.py` script must be able to verify deterministic match.
*   **Math-First Cognition:** Prevent LLM hallucinations by using deterministic Python tools for all quantitative forecasting. The LLM's role is strictly to translate these mathematical outputs into the negotiation payload.
*   **Deterministic Firewall:** The Execution Node acts as a strict firewall. All proposals must pass hardcoded constraints (e.g., `WHITELISTED_ASSETS`, `MAX_TRANSACTION_VALUE_USD`, `ALLOWED_HOOKS`).
*   **Decimals Discipline:** Use base-units strings (e.g., "1000000" for 1.0 USDC) throughout the pipeline to avoid float errors.
*   **Iterative Development & Frequent Commits:** Comply with hackathon requirements by working iteratively. Break down tasks into small, logical units and commit work frequently with descriptive messages.
*   **Living Documentation:** Continuously update `README.md`, `GEMINI.md`, and `docs/` to reflect the current state. Documentation must NEVER lag behind implementation.
*   **Compliance First:** All changes must pass the `scripts/check_bounty_compliance.py` gate (Day 9+).
