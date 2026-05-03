# Arbiter Capital

Autonomous multi-agent DeFi treasury system built for ETHGlobal Open Agents (deadline 2026-05-06).

Two LangGraph agents (Quant + Patriarch) negotiate swap proposals over a live Gensyn AXL network, reach 2-of-3 multisig consensus, and execute Uniswap v4 swaps through a Gnosis Safe — with every LLM call and decision persisted to 0G decentralised storage.

**Bounty targets:** Gensyn AXL ($5k) · 0G Storage ($15k) · KeeperHub Best Use ($4.5k + $500 feedback) · Uniswap v4 Hook ($5k) · Grand Prize

---

## Architecture

```
market_injector.py          injects price scenarios
       |
  [AXL topic: MARKET_DATA]
       |
quant_process.py            LangGraph: ingest → recall → draft → audit → sign (EIP-712)
       |
  [AXL topic: PROPOSALS]
       |
patriarch_process.py        LangGraph: recheck → evaluate → sign (KeeperHub sim oracle)
       |
  [AXL topic: FIREWALL_CLEARED + CONSENSUS_SIGNATURES]
       |
execution_process.py        ecrecover 2-of-3 threshold → Safe.execTransaction → Uniswap v4
       |
  [Sepolia] ArbiterThrottleHook → PoolManager → swap
            ArbiterReceipt SBT minted to Safe

byzantine_watchdog.py       publishes adversarial proposals (A1-A6 attacks) for demo
monitor_network.py          4-pane God View: AXL stream / Treasury / Audit Chain / Watchdog
```

All inter-process messages are Pydantic models over Gensyn AXL (SQLite mock in dev, real AXL in demo). Every LLM call is captured as a `LLMContext` artifact written to 0G storage and indexed in ChromaDB for semantic recall.

---

## Deployed Contracts (Sepolia)

| Contract | Address | Etherscan |
|---|---|---|
| Gnosis Safe (2-of-3) | `0xd42C17165aC8A2C69f085FAb5daf8939f983eB21` | [view](https://sepolia.etherscan.io/address/0xd42C17165aC8A2C69f085FAb5daf8939f983eB21) |
| ArbiterThrottleHook | `0x4Fb70855Af455680075d059AD216a01A161800C0` | [view](https://sepolia.etherscan.io/address/0x4Fb70855Af455680075d059AD216a01A161800C0) |
| ArbiterReceipt SBT | `0x47D6414fbf582141D4Ce54C3544C14A6057D5a04` | [view](https://sepolia.etherscan.io/address/0x47D6414fbf582141D4Ce54C3544C14A6057D5a04) |

---

## Setup

### Prerequisites

- Python 3.11+, Node 18+
- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`forge`, `cast`)
- [uv](https://github.com/astral-sh/uv) for Python package management

### Install

```bash
# Clone
git clone https://github.com/jmberean/arbiter-capital.git
cd arbiter-capital

# Python venv (Windows)
python -m venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt

# Foundry dependencies (submodules)
git submodule update --init --recursive
```

### Environment

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Key variables:

```env
# RPC + keys
ETH_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/<your-key>
SEPOLIA_RPC=https://eth-sepolia.g.alchemy.com/v2/<your-key>
QUANT_PRIVATE_KEY=0x...
PATRIARCH_PRIVATE_KEY=0x...
EXECUTOR_PRIVATE_KEY=0x...

# Deployed addresses (already set for Sepolia)
SAFE_ADDRESS=0xd42C17165aC8A2C69f085FAb5daf8939f983eB21
ARBITER_THROTTLE_HOOK=0x4Fb70855Af455680075d059AD216a01A161800C0
ARBITER_RECEIPT_NFT=0x47D6414fbf582141D4Ce54C3544C14A6057D5a04

# AXL nodes (5 local nodes for demo)
AXL_NODE_URL_QUANT=http://127.0.0.1:9001
AXL_NODE_URL_PATRIARCH=http://127.0.0.1:9002
AXL_NODE_URL_EXEC=http://127.0.0.1:9003
AXL_NODE_URL_KEEPERHUB=http://127.0.0.1:9004
AXL_NODE_URL_WATCHDOG=http://127.0.0.1:9005
DEMO_MODE=1
```

---

## Running

### Local Demo (Recommended for Recording)

Due to hardcoded port conflicts in the `axl-node.exe` binary (9002/7000), running a full 5-node mesh on a single machine requires significant network workarounds. For the demo recording, we use the **SQLite Message Bus** simulation. This maintains the 5-process isolation and EIP-712 signing but avoids the binary's port collision.

1.  **Configure `.env`**:
    *   Set `DEMO_MODE=0`
    *   Set `SAFE_ADDRESS` to your real Sepolia Safe (for execution)
2.  **Start all daemons**:
    ```bash
    $env:PYTHONPATH="."; python scripts/start_all.py
    ```
3.  **Inject Scenario**:
    Choose `[1] Inject flash_crash_eth` from the interactive menu.

### Multi-Machine P2P (AXL Native)

To run in full decentralized mode:
1.  **Install AXL nodes** on separate machines or containers.
2.  **Configure `.env`**:
    *   Set `DEMO_MODE=1`
    *   Set `AXL_NODE_URL_QUANT`, etc. to the respective node addresses.
    *   Set `AXL_NODE_KEY_QUANT`, etc. for envelope signing.
3.  **Start daemons**: `python scripts/start_all.py`. The processes will fail-closed if they cannot reach the real AXL nodes.

---

## Tests

```bash
pytest tests/ -v
python scripts/check_bounty_compliance.py   # must exit 0 before submission
```

---

## Smart Contract Deployment (Foundry)

Contracts are already deployed on Sepolia. To redeploy:

```bash
# 1. Mine CREATE2 salt for ThrottleHook (takes seconds)
forge script script/HookMiner.s.sol --rpc-url sepolia -vvv
# Copy HOOK_SALT and ARBITER_THROTTLE_HOOK into .env

# 2. Deploy ThrottleHook
forge script script/DeployThrottleHook.s.sol \
    --rpc-url sepolia --private-key $DEPLOYER_KEY --broadcast --verify

# 3. Deploy ArbiterReceipt SBT
forge script script/DeployArbiterReceipt.s.sol \
    --rpc-url sepolia --private-key $DEPLOYER_KEY --broadcast --verify

# Or use the helper script (Windows PowerShell):
.\scripts\deploy.ps1 -SkipVerifyHook
```

---

## Key Docs

| Doc | Purpose |
|---|---|
| `docs/MANUAL_ACTION_REQUIRED.md` | Go-live checklist with dependency order |
| `docs/SYSTEM_DESIGN.md` | Full architecture and design decisions |
| `docs/TECHNICAL_ROADMAP.md` | Step-by-step implementation roadmap |
| `docs/KEEPERHUB_FEEDBACK.md` | KeeperHub builder feedback (bounty submission) |

---

## Audit Chain

Every decision is cryptographically chained and replayable:

```bash
# Verify the full audit chain
python verify_audit.py --walk-from-head

# Replay a specific LLM decision from 0G storage
python scripts/replay_decision.py <receipt_hash>
```
