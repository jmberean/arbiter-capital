# Arbiter Capital - Autonomous Family Office (v3.0)

## Project Overview

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across decentralized finance (DeFi). To solve the "black box" trust issue for institutional capital, the system splits AI cognition into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." 

These agents formulate structured proposals based on predictive models and debate them over a decentralized mesh network. Trades are only executed via a treasury Safe when cryptographically verifiable consensus is reached.

**Key Technologies & Architecture:**
*   **Agent Framework:** Python-based LangGraph.
*   **LLM:** Claude 3.5 Sonnet.
*   **Networking:** Gensyn AXL for decentralized P2P agent communication.
*   **Execution & Custody:** KeeperHub (MCP) integrated with a Safe (Smart Account) for deterministic execution.
*   **DeFi Target:** Uniswap v4 (specifically targeting Hooks).
*   **Dual-Layer Memory:** 
    *   **Base Layer:** 0G (Layer 1 testnet) for an immutable audit trail.
    *   **Retrieval Layer:** ChromaDB (Vector DB) for agent recall via semantic search.

The system relies on a three-process topology:
1.  **Process 1 (The Quant):** Math-first cognition using quantitative Python scripts to identify yield opportunities.
2.  **Process 2 (The Patriarch):** Focuses on capital preservation and risk management.
3.  **Process 3 (Execution Node & Firewall):** A deterministic Python runtime (No LLM) that enforces safety constraints before routing payloads to KeeperHub.

## Building and Running

*(Note: The codebase is currently in the design phase. The following are anticipated commands based on the system design document.)*

*   **Environment Setup:** `TODO: Add setup instructions (e.g., pip install, environment variables for API keys and network configs).`
*   **Running the Network:** The architecture requires three separate processes to prove decentralization.
    *   `TODO: Command to run Process 1 (Quant) bound to AXL Node A.`
    *   `TODO: Command to run Process 2 (Patriarch) bound to AXL Node B.`
    *   `TODO: Command to run Process 3 (Execution Node & Firewall).`
*   **Demo Mode:** 
    *   To simulate market conditions and force agent interaction for demos, run: `python market_god.py` (This injects a synthetic market crisis into the Quant's ingestion node).

## Development Conventions

*   **Deterministic Safety:** The Execution Node acts as a strict firewall. All proposals must pass hardcoded constraints (e.g., `WHITELISTED_ASSETS`, `MAX_TRANSACTION_VALUE_USD`).
*   **Structured Negotiation:** Agents must not use freeform chat for debates. All communication over the AXL network must strictly adhere to the defined `Proposal` JSON schema.
*   **Math-First Approach:** Prevent LLM hallucinations by using deterministic Python tools for all quantitative forecasting and risk analysis. The LLM's role is strictly to translate these mathematical outputs into the structured negotiation payload.
*   **Immutable Auditing:** Every decision, transcript, and execution hash must be written to the 0G Layer 1 testnet.
*   **Deep Reasoning:** Always prioritize depth, quality, and rigorous thinking over speed. Take the time necessary to deeply analyze tasks, consider edge cases, and ensure robust, high-quality output rather than rushing to provide a fast response.
