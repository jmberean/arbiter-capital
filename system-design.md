Here is the finalized v3.0 architecture. This version patches the technical vulnerabilities, upgrades the institutional narrative with a Smart Account structure, grounds the agents in actual quantitative math, and ensures the 3-minute demo is entirely deterministic.

***

# System Design Specification: Autonomous Family Office (v3.0)

**Project:** Autonomous Multi-Agent Treasury Manager
**Target Event:** ETHGlobal Open Agents (April 24 – May 6, 2026)
**Architecture Paradigm:** Isolated Multi-Agent Runtimes (LangGraph) + Decentralized P2P Networking (AXL) + Deterministic Execution via Smart Accounts (KeeperHub / Safe) + Dual-Layer Memory (0G / Vector DB)

---

## 1. System Overview & Problem Statement
**The Problem:** Maximizing yield across decentralized finance requires constant monitoring and high-frequency execution. While AI agents can calculate optimal routes, institutional and high-net-worth capital will not trust a "black box" algorithm to manage funds autonomously due to hallucination risks and lack of explainability.
**The Solution:** The "Autonomous Family Office." The AI's cognition is split into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." They formulate structured proposals backed by state-of-the-art predictive models and debate them over a decentralized mesh network. The system only executes a trade via a treasury Safe when cryptographically verifiable consensus is reached, creating a fully transparent, auditable, and automated protocol.

## 2. Hackathon Bounty Strategy
* **Gensyn ($5k):** Agents run on *physically separate* Python LangGraph processes and communicate strictly via Gensyn AXL, satisfying the "Agent Town" true P2P requirement.
* **KeeperHub ($4.5k + $500 Feedback):** Deep integration via MCP to act as an execution delegate for a smart account treasury.
* **0G ($15k):** Serves as the protocol's permanent Base Layer memory. Every proposal, debate transcript, and execution hash is written to the 0G Layer 1 as an immutable audit trail.
* **Uniswap ($5k):** Testnet execution specifically targeting **Uniswap v4 Hooks** (e.g., routing trades through pools with Volatility Oracle or KYC/Whitelist hooks) to align with Uniswap's current roadmap.

---

## 3. Core Architecture & Topology
To prove decentralization, the system abandons the single global LangGraph orchestrator. It operates via three distinct processes.

### Process 1: The Quant (Agent 1 Runtime)
* **Objective:** Identify yield opportunities (e.g., rotating ETH into higher-yield SOL staking derivatives or Uniswap liquidity pools).
* **Stack:** Dedicated LangGraph instance + Quantitative Python Scripts + LLM (Claude 3.5 Sonnet).
* **Network:** Runs locally, bound to AXL Node A.

### Process 2: The Patriarch (Agent 2 Runtime)
* **Objective:** Capital preservation, strict adherence to drawdown limits, and portfolio stability.
* **Stack:** Dedicated LangGraph instance + LLM (Claude 3.5 Sonnet).
* **Network:** Runs locally, bound to AXL Node B.

### Process 3: The Execution Node & Policy Firewall
* **Objective:** Enforces deterministic safety rules and routes approved payloads to KeeperHub.
* **Stack:** Standard Python runtime (No LLMs) + KeeperHub MCP.

---

## 4. The Quant's Brain (Math-First Cognition)
To prevent LLM hallucination in financial decision-making, the Quant agent does not guess market movements. It utilizes a LangGraph tool-calling architecture to execute actual mathematical forecasting.
1.  **Quantitative Ingestion:** The LangGraph node executes a Python tool that runs custom, state-of-the-art price prediction models against live or simulated market data.
2.  **LLM Translation:** The quantitative output (e.g., "Predicted 48-hour ETH volatility exceeds 12%; SOL staking yield spread +2.1%") is injected into the LLM's context.
3.  **Proposal Generation:** Claude 3.5 Sonnet translates the math into a structured negotiation payload to present to the Patriarch over the AXL network.

---

## 5. The Structured Negotiation Protocol
Freeform LLM chat is unparseable for smart contracts. Agents debate using a strict JSON schema passed over the AXL network.

**The `Proposal` Schema:**
```json
{
  "proposal_id": "prop_8f72c",
  "target_protocol": "Uniswap_V4",
  "v4_hook_required": "Volatility_Oracle",
  "action": "SWAP",
  "asset_in": "WETH",
  "asset_out": "USDC",
  "amount_in": 15.5,
  "projected_apy": 8.4,
  "risk_score_evaluation": 4.2,
  "rationale": "High-conviction rotation based on predictive momentum models; routing via v4 Oracle hook to mitigate slippage.",
  "consensus_status": "PENDING" // Transitions to ACCEPTED or REJECTED
}
```

---

## 6. The Deterministic Policy Firewall
The finalized `ACCEPTED` JSON payload passes through a strict Python firewall before touching the blockchain to guarantee institutional safety.

**Hardcoded Constraints:**
* `WHITELISTED_ASSETS = ["WETH", "USDC", "SOL"]`
* `MAX_TRANSACTION_VALUE_USD = 50000`
* `REQUIRED_ARCHITECTURE = "Uniswap_v4"`

If the LLM payload violates *any* deterministic rule, the transaction is killed, an error is returned to the AXL network, and execution halts.

---

## 7. Execution & Smart Account Architecture
A family office does not use an Externally Owned Account (EOA).
1.  **Treasury Setup:** A testnet **Safe** (formerly Gnosis Safe) is deployed to hold the mock treasury assets.
2.  **KeeperHub Delegation:** KeeperHub is set up as an authorized delegate/module for the Safe.
3.  **Execution Routing:** The validated JSON proposal is translated into EVM calldata via the KeeperHub MCP. KeeperHub executes the trade on Uniswap v4 on behalf of the Safe, proving institutional-grade custody mechanics.

---

## 8. Dual-Layer Memory (The 0G Audit Trail)
0G is a Data Availability layer, not a database. We utilize a dual-layer architecture to provide actionable memory to the agents.
1.  **The Base Layer (0G):** After every successful trade, the complete "Decision Receipt" (JSON proposal, AXL transcript, execution hash) is permanently written to the 0G Layer 1 testnet.
2.  **The Retrieval Layer (ChromaDB):** The semantic embeddings of the debate and the corresponding **0G block hash** are stored in a local, lightweight vector database.
3.  **Agent Recall:** When agents need historical context, they run a semantic search against the local DB, retrieve the 0G hash, and pull the raw, mathematically verifiable receipt from the 0G network to inform their next debate.

---

## 9. Demo Execution Strategy (The "Market God" Script)
To ensure a flawless, high-stakes 3-minute recording without waiting for live testnet yields to shift, the repository includes a `market_god.py` script.
* **Function:** When executed, it injects a synthetic market crisis (e.g., "Flash crash: ETH drops 15% in 5 minutes") directly into the Quant's quantitative ingestion node.
* **Result:** This guarantees the agents immediately launch into a dramatic, high-stakes AXL negotiation perfectly on cue for the judges.

http://googleusercontent.com/interactive_content_block/0