# Arbiter Capital - Technical Roadmap & Implementation Plan (v3.0)

This document provides a highly technical, step-by-step roadmap for implementing the Arbiter Capital Autonomous Family Office, as specified in `SYSTEM_DESIGN.md`. The implementation is broken down into structured Minimum Viable Products (MVPs) to ensure systematic progress from local simulation to full decentralized execution.

---

## MVP 1: Core Agent Framework, Negotiation & Deterministic Firewall (Local Simulation)
**Objective:** Establish the three isolated processes, enforce the structured JSON negotiation protocol, and implement the deterministic safety firewall. In this phase, Gensyn AXL is simulated locally (e.g., via ZeroMQ or local REST/WebSockets) to accelerate core logic development.

### Step 1: Project Scaffolding & Core Configuration
*   Initialize Python virtual environment.
*   Define `requirements.txt` (`langgraph`, `langchain-anthropic`, `pydantic`, `python-dotenv`, etc.).
*   Set up `.env` for API keys (Anthropic) and initial configuration parameters.
*   Establish the directory structure (`/agents`, `/core`, `/execution`, `/memory`).

### Step 2: Data Models & Structured Protocols (`models.py`)
*   Implement strict Pydantic models for the `Proposal` schema defined in the design doc.
*   Ensure the schema includes `proposal_id`, `target_protocol`, `v4_hook_required`, `action`, `asset_in`, `asset_out`, `amount_in`, `projected_apy`, `risk_score_evaluation`, `rationale`, and `consensus_status`.
*   Implement validation logic to ensure no freeform LLM outputs can bypass the schema.

### Step 3: Process 3 - Execution Node & Policy Firewall (`firewall.py`)
*   Create a pure Python (No LLM) runtime script.
*   Implement hardcoded constraints:
    *   `WHITELISTED_ASSETS = ["WETH", "USDC", "SOL"]`
    *   `MAX_TRANSACTION_VALUE_USD = 50000`
    *   `REQUIRED_ARCHITECTURE = "Uniswap_v4"`
*   Build a validation engine that ingests an `ACCEPTED` Proposal JSON and either returns a "CLEARED" status or throws a specific constraint violation error.

### Step 4: The Market God Script (`market_god.py`)
*   Implement a script to generate synthetic market data (e.g., JSON payloads simulating price feeds, volatility spikes, and flash crashes).
*   Create endpoints/pipes to inject this data directly into the Quant agent's ingestion pipeline to force deterministic behavior during demos.

### Step 5: Process 1 - The Quant Agent (`quant.py`)
*   Initialize a LangGraph instance dedicated to the Quant persona.
*   Implement the "Math-First" tool: A deterministic Python function that ingests `market_god` data and outputs raw quantitative metrics (e.g., predicted 48h volatility).
*   Integrate Claude 3.5 Sonnet to translate the mathematical output into a valid `Proposal` payload.
*   Build the negotiation loop: Propose -> Receive feedback -> Adjust mathematical parameters -> Propose again.

### Step 6: Process 2 - The Patriarch Agent (`patriarch.py`)
*   Initialize a LangGraph instance dedicated to the Risk Patriarch persona.
*   Implement systemic prompt engineering focused on capital preservation and strict drawdown limits.
*   Build the critique loop: Ingest `Proposal` -> Evaluate against risk parameters -> Output `Proposal` with updated `consensus_status` (REJECTED with feedback, or ACCEPTED).

### Step 7: Local Orchestration (Mock AXL)
*   Write a temporary orchestrator (`mock_network.py`) to handle the message passing of the Pydantic `Proposal` objects between Process 1 and Process 2 until consensus is reached, then route the finalized proposal to Process 3.

---

## MVP 2: Decentralized Networking & Immutable Memory
**Objective:** Replace local simulation with actual decentralized infrastructure, integrating Gensyn AXL for P2P communication and establishing the Dual-Layer Memory (0G + ChromaDB).

### Step 1: Gensyn AXL Integration
*   Integrate the Gensyn AXL SDK.
*   Refactor Process 1 to bind to AXL Node A.
*   Refactor Process 2 to bind to AXL Node B.
*   Replace the `mock_network.py` with actual AXL message broadcasting and subscribing, ensuring only strictly typed JSON payloads are transmitted.

### Step 2: Vector Database Setup (ChromaDB)
*   Integrate ChromaDB as the local Retrieval Layer.
*   Implement embedding functions (using OpenAI or local models) to convert debate transcripts and rationales into searchable vectors.

### Step 3: 0G Layer 1 Integration (The Base Layer)
*   Connect to the 0G Layer 1 Testnet RPC.
*   Implement a service (`memory_writer.py`) that constructs a "Decision Receipt" (Proposal JSON + AXL Transcript + timestamp) and submits it as a transaction to the 0G network.
*   Capture the returning 0G block hash.

### Step 4: The Recall Pipeline
*   Link 0G and ChromaDB: Store the semantic embeddings of the debate in ChromaDB alongside the corresponding 0G block hash as metadata.
*   Implement a LangGraph tool for both agents: `query_historical_decisions(query_string)`. This tool searches ChromaDB, retrieves the 0G hash, fetches the immutable receipt from 0G, and injects it into the LLM context.

---

## MVP 3: Smart Account Execution & DeFi Routing
**Objective:** Connect the deterministic firewall to real on-chain execution via KeeperHub, targeting a Safe treasury and Uniswap v4.

### Step 1: Treasury Deployment
*   Deploy a Safe (Smart Account) on the target testnet (e.g., Sepolia or Base Sepolia).
*   Fund the testnet Safe with mock WETH, USDC, and SOL.

### Step 2: KeeperHub MCP Integration
*   Set up KeeperHub (Model Context Protocol).
*   Configure KeeperHub as an authorized delegate/module for the testnet Safe.
*   Integrate the KeeperHub SDK into Process 3 (`firewall.py`).

### Step 3: Uniswap v4 Routing Logic
*   Implement the translation layer inside Process 3 / KeeperHub: Convert the "CLEARED" `Proposal` JSON into specific EVM calldata targeting the Uniswap v4 router.
*   Implement the logic to target specific v4 Hooks as required by the proposal (e.g., routing through a Volatility Oracle hook pool).

### Step 4: End-to-End System Test
*   Run the complete 3-process topology on the AXL network.
*   Trigger `market_god.py` to initiate a crisis.
*   Observe Quant formulation -> AXL transmission -> Patriarch debate -> Consensus -> Firewall validation -> 0G auditing -> KeeperHub EVM execution on Uniswap v4.

---

## MVP 4: Loop Closure & Advanced DeFi Routing (COMPLETED)
**Objective:** Harden decision-making with self-correction loops, expand audit trails, and implement v4 Hook routing.

### Key Deliverables
*   **Quant Feedback Loop:** Implemented iterative proposal generation in `agents/quant.py`.
*   **Uniswap v4 Hook Support:** Integrated `Volatility_Oracle` and `Dynamic_Fee` routing in `router.py`.
*   **Expanded Audit Trail:** Updated `patriarch_process.py` to store complete negotiation transcripts on 0G.
*   **End-to-End Negotiation Test:** Verified 3-round debate reaching consensus and execution.

---

## MVP 5: Live Infrastructure & Testnet Pilot (COMPLETED)
**Objective:** Transition from local simulation to actual on-chain execution on decentralized testnets.

### Key Deliverables
*   **Live 0G Audit Trail:** Integrated real 0G Layer 1 Testnet RPC for immutable decision logging.
*   **Safe Multisig Integration:** Upgraded `SafeTreasury` to build and sign real Safe transactions using `gnosis-py`.
*   **Uniswap v4 Live Routing:** Implemented real EVM calldata encoding with `eth_abi` targeting v4 testnet addresses.
*   **Hybrid AXL Networking:** Enhanced the P2P layer to support real Gensyn AXL node communication with mock fallbacks.

---

## MVP 6: Full Live Pilot & Stress Testing (IN PROGRESS)
**Objective:** Harden the decentralized consensus mechanism and verify system resilience under extreme market conditions.

### Step 1: Cryptographic Consensus Signatures (COMPLETED)
*   Implement EIP-712 transaction hash generation for every proposal.
*   Patriarch signs the hash using a private key upon reaching consensus.
*   Broadcast the cryptographic signature over the AXL network via the `CONSENSUS_SIGNATURES` topic.

### Step 2: Multisig Verification & Collection (COMPLETED)
*   Refactor the Execution Node to collect and verify signatures from the network.
*   Enforce the threshold (e.g., 2-of-2 or 1-of-1 for pilot) before dispatching to the Safe.

### Step 3: Real-world Stress Scenarios
*   **Scenario: Gas War:** Inject data with extreme gas prices to verify "Cost vs. Yield" reasoning.
*   **Scenario: Protocol Hack:** Simulate a critical safety score drop on a protocol to verify emergency withdrawal speed.
*   **Scenario: Multi-Agent Contention:** Force the agents into a 3-round disagreement to test negotiation convergence.

### Step 4: Audit Verification Tooling
*   Build `verify_audit.py` to cross-reference 0G Testnet transaction data with local ChromaDB semantic indices.
*   Ensure every "Live Pilot" execution is verifiable by independent third parties.

---

## MVP 7: Final Polish & Demo Readiness
**Objective:** Optimize the system for the final hackathon presentation and ensure 100% reliability for the live demo.

### Step 1: Performance Optimization & Resilience
*   Implement robust reconnection logic for AXL and 0G RPC.
*   Optimize the retrieval layer (ChromaDB) for low-latency agent recall.
*   Ensure all processes can be restarted and resume state from the AXL message history.

### Step 2: Monitoring & Dashboard (CLI/Web)
*   Develop a terminal-based dashboard (`monitor_network.py`) to visualize AXL message flow in real-time.
*   Provide a "God View" of the Safe treasury balance and current yield positions.

### Step 3: Final Documentation & Video Preparation
*   Update `README.md` and `GEMINI.md` with final setup instructions and architectural diagrams.
*   Prepare the demo script for the hackathon video, showcasing the full "Consensus -> Execution -> Audit" lifecycle.
