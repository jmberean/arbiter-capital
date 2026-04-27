# Arbiter Capital — Autonomous Family Office (v5.0 — "Winning Edition")

**Arbiter Capital** is an autonomous, multi-agent DeFi treasury manager designed for institutional-grade capital management. To solve the "black box" trust issue, the system employs **cognitive isolation** across a 4-persona "Agent Town," cryptographic accountability via EIP-712 signatures, and reproducible AI memory on the 0G Layer 1.

Built for the **ETHGlobal Open Agents** hackathon, Arbiter Capital moves beyond simple chatbots to a fully autonomous, adversarial-resilient execution engine.

## 🏛️ Architecture: The Agent Town

Cognition is split into four isolated personas communicating exclusively over the **Gensyn AXL** decentralized P2P mesh:

1.  **The Yield Quant (P1):** Math-first cognition using quantitative tools (GARCH, Kelly Criterion) to identify alpha.
2.  **The Risk Patriarch (P2):** Conservative guardian focusing on capital preservation and risk-adjusted returns.
3.  **The Sim-Oracle Auditor (P3):** Powered by **KeeperHub MCP**, providing real-time fork-simulation as a consensus signal.
4.  **The Byzantine Watchdog (P4):** An adversarial process that attempts to corrupt the network, proving the system's resilience on-camera.

Execution is handled by a deterministic **Execution Node (Firewall)** that enforces hardcoded safety constraints before routing trades to a **2-of-2 Sepolia Safe**.

## 🚀 Elite Features (v5.0)

*   **🎯 ArbiterThrottleHook:** A custom Uniswap v4 hook deployed on Sepolia that prevents self-MEV by throttling consecutive swaps within a TWAP window.
*   **🧠 0G AI Memory Substrate:** Every LLM call (system prompt, messages, model ID, response) is hash-chained to the 0G Layer 1, making AI decisions cryptographically reproducible via `scripts/replay_decision.py`.
*   **🛂 KeeperHub Sim Oracle:** KeeperHub is integrated as a consensus participant, vetoing proposals that revert in simulation before any gas is spent.
*   **🐺 Byzantine Resilience:** The system is built to detect and reject scripted attacks (forged math, invalid signatures, replay nonces) in real-time.
*   **🎟️ Soulbound Decision Receipts:** Every successful execution mints an ERC-721 SBT to the Safe, linking the on-chain trade to its 0G audit trail.
*   **🔍 Public Verifier:** A QR-served verifier page allows anyone to walk the 0G audit chain and verify the integrity of the AI's cognition.

## 🛠️ Tech Stack

*   **Agent Framework:** Python-based LangGraph.
*   **Networking:** Gensyn AXL (Serverless, encrypted P2P mesh).
*   **Memory:** 0G Layer 1 (Canonical AI Memory) + ChromaDB (Local Recall).
*   **Execution:** KeeperHub (Safe Module & MCP) + Uniswap v4 (Hooks & Universal Router).
*   **Trust Layer:** EIP-712 signatures for all agent-to-agent negotiations.

## 🏁 Roadmap (v5.0 "Winning Sprint")

*   **MVP 1-5:** COMPLETED (Core Framework, Multi-Process P2P, Dual-Layer Memory).
*   **MVP 6 (Current):** **Winning Edition Hardening.** Implementing EIP-712, true 2-of-2 Safe execution, ArbiterThrottleHook, and 0G LLM Substrate.
*   **MVP 7:** Byzantine Watchdog & Public Verifier UI.

## ⚡ Getting Started

### Environment Setup
1.  `uv venv` && `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix).
2.  `uv pip install -r requirements.txt`
3.  `cp .env.example .env` and insert your API keys (OpenAI, 0G, KeeperHub, Sepolia).

### Running the Network
The architecture requires five separate processes to prove decentralization. Ensure `AXL_NODE_URL_*` are configured in your `.env`.

1.  **AXL Mesh:** Run `bash scripts/setup_axl.sh` to bring up the 5 P2P nodes.
2.  **The Quant:** `python quant_process.py`
3.  **The Patriarch:** `python patriarch_process.py`
4.  **The Execution Node:** `python execution_process.py`
5.  **Sim Oracle:** Ensure the KeeperHub MCP server is running.
6.  **The Watchdog:** `python byzantine_watchdog.py` (For demo/adversarial testing).

### Verifying the Audit
`python verify_audit.py --walk-from-head`

---
*For detailed specifications, see `docs/SYSTEM_DESIGN.md` and `docs/TECHNICAL_ROADMAP.md`.*
