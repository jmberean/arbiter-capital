# Arbiter Capital - Autonomous Family Office (v3.0)

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across decentralized finance (DeFi). To solve the "black box" trust issue for institutional capital, the system splits AI cognition into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." 

These agents formulate structured proposals based on predictive models and debate them over a decentralized mesh network. Trades are only executed via a treasury Safe when cryptographically verifiable consensus is reached.

## Core Architecture & Topology

The system operates via three distinct processes to ensure decentralization and safety:

1.  **Process 1: The Quant (Agent 1 Runtime)**
    *   **Objective:** Identify yield opportunities using math-first cognition.
    *   **Stack:** LangGraph + Python Quantitative Scripts + OpenAI (gpt-5.4-nano).
2.  **Process 2: The Patriarch (Agent 2 Runtime)**
    *   **Objective:** Capital preservation and strict adherence to drawdown limits.
    *   **Stack:** LangGraph + OpenAI (gpt-5.4-nano).
3.  **Process 3: The Execution Node & Policy Firewall**
    *   **Objective:** Enforces deterministic safety rules and routes authorized payloads to the Safe (Smart Account).
    *   **Stack:** Deterministic Python runtime (Safe-ETH-Py + Web3.py).

## Getting Started (Local Decentralized Simulation)

The current MVP 3 implements a full 3-process topology with smart account execution simulation and Uniswap v4 routing logic.

### Prerequisites

*   Python 3.10+
*   OpenAI API Key

### Setup

1.  Create a virtual environment and install dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  Copy the example environment file and add your API key:
    ```bash
    cp .env.example .env
    ```
    *Edit `.env` and set your `OPENAI_API_KEY`.*

### Running the End-to-End Simulation

To simulate the decentralized network, you must run the isolated processes in separate terminal windows.

**Terminal 1: Start the Quant Agent (Process 1)**
```bash
python quant_process.py
```

**Terminal 2: Start the Risk Patriarch (Process 2)**
```bash
python patriarch_process.py
```

**Terminal 3: Start the Execution Node (Process 3)**
```bash
python execution_process.py
```

**Terminal 4: Inject Market Data (Demo Trigger)**
```bash
python market_injector.py flash_crash_eth
```

This will instantly trigger the `flash_crash_eth` scenario. The Quant will detect the crash, formulate a high-conviction rotation strategy, and publish it to the local AXL broker. The Patriarch will automatically receive the proposal, evaluate it, and (if accepted) pass it to the Policy Firewall. Upon clearing the firewall, the Execution Node will generate Uniswap v4 calldata and route it through the Safe Smart Account.
