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
- [Go 1.21+](https://go.dev/dl/) (for building `axl-node`)
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

### AXL Node Setup

Each daemon runs its own `axl-node` instance on a distinct port, giving 5 independent Yggdrasil identities on the live Gensyn mesh. Build the binary once, then use the setup script to start all nodes.

```bash
# 1. Build axl-node from source (requires Go 1.21+)
git clone https://github.com/gensyn-ai/axl /tmp/axl
cd /tmp/axl && make build
cp ./node /opt/homebrew/bin/axl-node   # or any directory on your PATH

# 2. Start all 5 nodes (generates keys on first run, connects to live Gensyn peers)
bash scripts/setup_axl.sh
```

The script creates `state/axl/<name>.pem` keys and `state/axl/<name>-config.json` configs, starts each node in the background, then prints a health check. Node logs land in `state/axl_logs/`. Stop them with `pkill -f axl-node`.

Port assignments (HTTP API / internal TCP):

| Daemon | API port | TCP port |
|--------|----------|----------|
| quant | 9011 | 7011 |
| patriarch | 9012 | 7012 |
| exec | 9013 | 7013 |
| keeperhub | 9014 | 7014 |
| watchdog | 9015 | 7015 |

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

# AXL — each daemon connects to its own axl-node instance (setup_axl.sh)
AXL_NODE_URL_QUANT=http://127.0.0.1:9011
AXL_NODE_URL_PATRIARCH=http://127.0.0.1:9012
AXL_NODE_URL_EXEC=http://127.0.0.1:9013
AXL_NODE_URL_KEEPERHUB=http://127.0.0.1:9014
AXL_NODE_URL_WATCHDOG=http://127.0.0.1:9015
# AXL_PEER_KEYS is auto-written by setup_axl.sh — do not set manually
DEMO_MODE=1

# Cap on-chain swap size during testing (remove or raise for production)
MAX_SWAP_UNITS=100000000000000000   # 0.1 WETH
```

### Account Funding

| Account | Key in `.env` | Needs funding? | What & how much |
|---|---|---|---|
| **Executor** | `EXECUTOR_PRIVATE_KEY` | Yes | ~0.05 Sepolia ETH for gas (pays `execTransaction` on the Safe) |
| **Safe** | `SAFE_ADDRESS` (multisig) | Yes | WETH or USDC to swap — quant defaults to ~1 WETH; set `MAX_SWAP_UNITS` to cap it |
| **0G account** | `ZERO_G_PRIVATE_KEY` | Optional | ~0.005 0G testnet ETH per run for on-chain audit writes; falls back to local files if dry |
| **Quant** | `QUANT_PRIVATE_KEY` | No | EIP-712 signing only — no gas needed |
| **Patriarch** | `PATRIARCH_PRIVATE_KEY` | No | EIP-712 signing only — no gas needed |

---

## Running

### Local Demo (Recommended for Recording)

1.  **Build `axl-node`** (one-time, requires Go 1.21+):
    ```bash
    git clone https://github.com/gensyn-ai/axl /tmp/axl
    cd /tmp/axl && go build -o axl-node ./cmd/node
    sudo mv axl-node /usr/local/bin/
    ```
2.  **Start all 5 AXL nodes** (leave running in background):
    ```bash
    bash scripts/setup_axl.sh
    ```
    This generates per-daemon ed25519 keys, starts a hub-spoke Yggdrasil mesh on ports 9011–9015, and writes `AXL_PEER_KEYS` to `.env` automatically. Stop them at any time with `pkill -f axl-node`.
3.  **Start all daemons**:
    ```bash
    PYTHONPATH=. python scripts/start_all.py
    ```
4.  **Inject Scenario**: Choose `[1] Inject flash_crash_eth` from the interactive menu.

Daemons fail-closed if `DEMO_MODE=1` and their AXL node is unreachable. Restart nodes with `bash scripts/setup_axl.sh` if needed.

### Multi-Machine P2P (AXL Native)

To distribute nodes across machines, run `setup_axl.sh` on each machine (it connects outbound to the public Gensyn peers — no inbound port forwarding needed). Point each `AXL_NODE_URL_*` in `.env` to the corresponding machine's API port.

> **Note:** `setup_axl.sh` configures spoke nodes to peer through `tls://127.0.0.1:9021` (the local quant hub). For multi-machine deployments, replace that address in the script with the quant machine's reachable IP/hostname before running on the other machines.

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
