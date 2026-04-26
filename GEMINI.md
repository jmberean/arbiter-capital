# Arbiter Capital - Autonomous Family Office (v3.0)

## Project Overview

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across decentralized finance (DeFi). To solve the "black box" trust issue for institutional capital, the system splits AI cognition into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." 

These agents formulate structured proposals based on predictive models and debate them over a decentralized mesh network. Trades are only executed via a treasury Safe when cryptographically verifiable consensus is reached.

**Key Technologies & Architecture:**
*   **Agent Framework:** Python-based LangGraph.
*   **LLM:** OpenAI GPT-4o (Production) and gpt-5.4-nano (Cost-efficient Testing/Development).
*   **Networking:** Gensyn AXL for decentralized P2P agent communication.
*   **Execution & Custody:** KeeperHub (MCP) integrated with a Safe (Smart Account) for deterministic execution.
*   **DeFi Target:** Uniswap v4 (specifically targeting Hooks), Lido (LSTs), and Pendle (Yield Trading).
*   **Dual-Layer Memory:** 
    *   **Base Layer:** 0G (Layer 1 testnet) for an immutable audit trail.
    *   **Retrieval Layer:** ChromaDB (Vector DB) for agent recall via semantic search.

The system relies on a three-process topology:
1.  **Process 1 (The Quant):** Math-first cognition using quantitative Python scripts to identify yield opportunities.
2.  **Process 2 (The Patriarch):** Focuses on capital preservation and risk management.
3.  **Process 3 (Execution Node & Firewall):** A deterministic Python runtime (No LLM) that enforces safety constraints before routing payloads to KeeperHub.

## Project Roadmap

The detailed implementation plan is tracked in [docs/TECHNICAL_ROADMAP.md](docs/TECHNICAL_ROADMAP.md).

*   **MVP 1-5:** COMPLETED (Core Framework, Multi-Process P2P, Dual-Layer Memory, Advanced Reasoning, Live Infrastructure).
*   **MVP 6:** IN PROGRESS (Full Live Pilot & Stress Testing).

## Live Infrastructure (In Development)

To transition from the current "Local Simulation" to a "Live Pilot," the following connections are required:
*   **Memory:** Real 0G Layer 1 Testnet RPC.
*   **Execution:** KeeperHub MCP linked to a deployed Safe Multisig.
*   **Networking:** Live Gensyn AXL nodes.
*   **Liquidity:** Uniswap v4 Testnet contracts.

*   **Environment Setup:** 
    1. `uv venv` (Creates a high-performance virtual environment)
    2. Activate the virtual environment:
       *   **Windows:** `.venv\Scripts\activate`
       *   **Unix/macOS:** `source .venv/bin/activate`
    3. `uv pip install -r requirements.txt` (Blazing fast dependency installation)
    4. `cp .env.example .env` and insert your API keys.
*   **Running the Network:** The architecture requires three separate processes to prove decentralization. Run these in separate terminal instances:
    *   **Process 1 (The Quant):** `python quant_process.py`
    *   **Process 2 (The Patriarch):** `python patriarch_process.py`
    *   **Process 3 (Execution Node):** `python execution_process.py`
*   **Demo Mode (Advanced Scenarios):** 
    *   `python market_injector.py flash_crash_eth`: Triggers rotation to stablecoin.
    *   `python market_injector.py protocol_hack`: Triggers emergency withdrawal.
    *   `python market_injector.py gas_war`: Tests cost-efficiency reasoning (Gas vs Yield).
    *   `python market_injector.py pendle_yield_arbitrage`: Massive yield on Pendle; triggers **Yield Trade** action.
    *   `python market_injector.py lst_expansion`: stETH yield surges; triggers **Stake LST** rotation.
    *   `python market_injector.py cross_chain_alpha`: Tests bridging logic.

## Development Conventions

*   **Deterministic Safety:** The Execution Node acts as a strict firewall. All proposals must pass hardcoded constraints (e.g., `WHITELISTED_ASSETS`, `MAX_TRANSACTION_VALUE_USD`).
*   **Structured Negotiation:** Agents must not use freeform chat for debates. All communication over the AXL network must strictly adhere to the defined `Proposal` JSON schema.
*   **Math-First Approach:** Prevent LLM hallucinations by using deterministic Python tools for all quantitative forecasting and risk analysis. The LLM's role is strictly to translate these mathematical outputs into the structured negotiation payload.
*   **Immutable Auditing:** Every decision, transcript, and execution hash must be written to the 0G Layer 1 testnet.
*   **Deep Reasoning:** Always prioritize depth, quality, and rigorous thinking over speed. Take the time necessary to deeply analyze tasks, consider edge cases, and ensure robust, high-quality output rather than rushing to provide a fast response.
*   **Iterative Development & Frequent Commits:** To comply with hackathon requirements and ensure the development process appears natural (not artificially generated), you MUST work iteratively. Do not commit large chunks of code or entire MVPs in a single commit. Break down tasks into small, logical units, and commit your work frequently with descriptive commit messages after completing each small milestone.
*   **Living Documentation:** As the project evolves, you MUST continuously update both `README.md` and `GEMINI.md` to reflect the current state of the architecture, setup instructions, and development conventions. Documentation should never lag behind implementation.
*   **Configuration Maintenance:** You MUST continuously keep project configuration files, specifically `.gitignore` and `requirements.txt`, updated as new dependencies are added or new files/directories need to be excluded from version control.
*   **Silent Planning & Execution:** When completing work or writing code, silently plan your steps, execute them, and thoroughly review your work before signing off. All of this MUST be done silently to avoid noisy, repetitive narration in the chat.
