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

## Getting Started (Local Simulation)

The current MVP implements a local simulation of the multi-agent negotiation process.

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

To run a simulation of the network, including market data injection, agent negotiation, and firewall validation:

```bash
python mock_network.py
```

This will trigger the `flash_crash_eth` scenario, prompting the Quant to formulate a high-conviction rotation strategy, which the Patriarch will then evaluate.
