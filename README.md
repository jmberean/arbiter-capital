# Arbiter Capital - Autonomous Family Office (v3.0)

**Arbiter Capital** is an Autonomous Multi-Agent Treasury Manager designed to maximize yield across decentralized finance (DeFi). To solve the "black box" trust issue for institutional capital, the system splits AI cognition into two isolated personas: an aggressive "Yield Quant" and a conservative "Risk Patriarch." 

These agents formulate structured proposals based on predictive models and debate them over a decentralized mesh network. Trades are only executed via a treasury Safe when cryptographically verifiable consensus is reached.

## Core Architecture & Topology

The system operates via three distinct processes to ensure decentralization and safety:

1.  **Process 1: The Quant (Agent 1 Runtime)**
    *   **Objective:** Identify yield opportunities using math-first cognition.
    *   **Stack:** LangGraph + Python Quantitative Scripts + GPT-5.4 nano.
2.  **Process 2: The Patriarch (Agent 2 Runtime)**
    *   **Objective:** Capital preservation and strict adherence to drawdown limits.
    *   **Stack:** LangGraph + GPT-5.4 nano.
3.  **Process 3: The Execution Node & Policy Firewall**
    *   **Objective:** Enforces deterministic safety rules and routes payloads to execution.
    *   **Stack:** Deterministic Python runtime (No LLMs).

## Getting Started (Local Decentralized Simulation)

The current MVP 2 implements a multi-process simulation of the decentralized network using a local message broker, along with a dual-layer memory system (0G mock + ChromaDB).

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
source venv/bin/activate
python quant_process.py
```

**Terminal 2: Start the Risk Patriarch (Process 2)**
```bash
source venv/bin/activate
python patriarch_process.py
```

**Terminal 3: Inject Market Data (Demo Trigger)**
```bash
source venv/bin/activate
python market_injector.py flash_crash_eth
```

This will instantly trigger the `flash_crash_eth` scenario. The Quant will detect the crash, formulate a high-conviction rotation strategy, publish it to the local AXL broker, and query ChromaDB/0G for historical context. The Patriarch will automatically receive the proposal from the network, evaluate it against the policy firewall, and write the immutable decision receipt to the dual-layer memory.
