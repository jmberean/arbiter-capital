# Arbiter Capital - Autonomous Family Office (v3.0)

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across decentralized finance (DeFi). The system splits AI cognition into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." 

These agents formulate structured proposals based on predictive models and debate them over a decentralized mesh network. Trades are only executed via a treasury Safe when cryptographically verifiable consensus is reached.

## Core Architecture & Topology

The system operates via three distinct processes to ensure decentralization and safety:

1.  **Process 1: The Quant (Agent 1 Runtime)**
    *   **Objective:** Identify yield opportunities using math-first cognition.
    *   **Stack:** LangGraph + Python Quantitative Scripts + OpenAI GPT-4o.
2.  **Process 2: The Patriarch (Agent 2 Runtime)**
    *   **Objective:** Capital preservation and strict adherence to drawdown limits.
    *   **Stack:** LangGraph + OpenAI GPT-4o.
3.  **Process 3: The Execution Node & Policy Firewall**
    *   **Objective:** Enforces deterministic safety rules and verifies multisig signatures before routing to the Safe.
    *   **Stack:** Deterministic Python runtime (Web3.py).

## Key Features (MVP 6)

*   **Cryptographic Consensus:** Agents broadcast EIP-712 Safe signatures over the AXL network.
*   **Multisig Verification:** Execution node collects signatures and only dispatches when the threshold is met.
*   **Dual-Layer Memory:** Decisions are logged permanently on **0G Layer 1** and indexed in **ChromaDB**.
*   **Auditability:** Standard tool included to verify decision integrity against the blockchain.
*   **Real-time Monitoring:** CLI Dashboard for live visualization of the agent mesh.

## Prerequisites

*   Python 3.10+
*   [uv](https://github.com/astral-sh/uv) (Highly recommended for high-performance environment management)
*   OpenAI API Key

## Setup

1.  Create a virtual environment and install dependencies:
    ```bash
    uv venv
    # Windows
    .venv\Scripts\activate
    # Unix/macOS
    source .venv/bin/activate

    uv pip install -r requirements.txt
    ```

2.  Copy the example environment file and add your API key:
    ```bash
    cp .env.example .env
    ```
    *Edit `.env` and set your `OPENAI_API_KEY`.*

## Running the System

To simulate the decentralized network, run the isolated processes in separate terminal windows.

**Terminal 1: Start the Network Monitor (The "God View")**
```bash
python monitor_network.py
```

**Terminal 2: Start the Quant Agent**
```bash
python quant_process.py
```

**Terminal 3: Start the Risk Patriarch**
```bash
python patriarch_process.py
```

**Terminal 4: Start the Execution Node**
```bash
python execution_process.py
```

**Terminal 5: Inject Market Data (Trigger Scenario)**
```bash
python market_injector.py flash_crash_eth
```

### Verification & Audit

After a trade is executed, you can verify the decision integrity on the 0G Layer 1:
```bash
python verify_audit.py
```

## Demo Scenarios

*   `flash_crash_eth`: Volatility spike triggers rotation to USDC via v4 Oracle Hook.
*   `protocol_hack`: Safety score crash triggers **Emergency Withdrawal**.
*   `gas_war`: Spikes gas to 850 Gwei; agents skip low-profit trades.
*   `pendle_yield_arbitrage`: Massive yield detected; triggers negotiation and execution.
