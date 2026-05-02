# Manual Action Required — Arbiter Capital Go-Live Checklist

**As of:** 2026-04-30 (updated 2026-04-30)
**Deadline:** 2026-05-06 (6 days remaining)
**Why this doc exists:** Everything below requires keys, wallets, running infrastructure, or
real-world experience that requires manual action.
Work through this list in order — later items depend on earlier ones.

---

## 1. Gensyn AXL — Live Node Deployment (Step 0.4) ✱ BOUNTY DISQUALIFIER

**Risk level: CRITICAL.** Without real AXL nodes the Gensyn bounty is void by definition.
The code already enforces this: `DEMO_MODE=1` without `AXL_NODE_URL_*` exits with code 1.

### What to do
- [x] 1. Read the live Gensyn AXL docs and pinned the binary version.
- [x] 2. Installed the AXL node binary (`axl-node.exe` present in repo root).
  - [x] a. Prerequisites confirmed.
  - [x] b. Pre-built Windows binary downloaded and placed on PATH.
  - [x] c. Node home dirs initialized for nodes 1–5.
  - [x] d. All 5 keypairs generated.
  - [x] e. `axl-node version` confirmed.
- [x] 3. Ran `bash scripts/setup_axl.sh` — 5 nodes launched on ports 9001–9005.
  - [x] a. Flags cross-checked against live AXL docs.
  - [x] b. Script verified and confirmed correct.
  - [x] c. Nodes launched via `scripts/setup_axl.sh`.
  - [x] d. God View Monitor confirms live AXL stream: MARKET_DATA (MarketGod), PROPOSALS (Quant_Node_A), PROPOSAL_EVALUATIONS (Patriarch_Node_B) all flowing.
- [x] 4. `.env` AXL URLs confirmed live (not placeholders): ports 9001–9005, `DEMO_MODE=1`.
- [x] 5. Compliance check: `DEMO_MODE=1` without AXL URL exits code 1 as expected; with URLs set, processes start cleanly.
- [x] 6. `monitor_network.py` (God View) shows ≥4 distinct senders active.

**Acceptance:** ✓ AXL stream live — Quant_Node_A, Patriarch_Node_B, MarketGod, Execution_Node confirmed in God View.

---

## 2. Sepolia ETH + Test Token Funding

Before any on-chain deployment, your deployer wallet needs gas money and the Safe needs
test tokens.

### What to do
- [x] 1. Get Sepolia ETH for the deployer wallet.
  - [x] a. Used **MetaMask wallet** (`0xba57...`) as the deployer/admin — required because Safe's web UI (https://app.safe.global) only accepts browser wallet connections, not raw private keys.
  - [x] b. Funded MetaMask with Sepolia ETH via faucet.
  - [x] c. Balance confirmed sufficient for Safe deployment + upcoming hook deploy.
  - [x] d. `EXECUTOR_PRIVATE_KEY` EOA (`0xba57...`) confirmed funded — successfully paid gas for ArbiterThrottleHook + ArbiterReceipt deployments.
- [x] 2. Get Sepolia test tokens for the Safe (Safe is deployed — see Step 3).
  - [ ] a. **WETH** — wrap Sepolia ETH from the Safe:
      - Open https://app.safe.global → your Safe → "New transaction" → "Contract interaction".
      - Contract: `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14` (Sepolia WETH9). Method: `deposit()`. Value: `0.1` ETH. Sign with both owners and execute.
  - [x] b. **USDC** — received 40 USDC via Circle Faucet (https://faucet.circle.com), sent directly to Safe address.
  - [ ] c. **stETH / WBTC** — open https://app.aave.com/faucet/?marketName=proto_sepolia_v3 → connect wallet → click "Faucet" beside stETH and WBTC → confirm in wallet → manually transfer the minted tokens from your EOA to `SAFE_ADDRESS` (Aave mints to the connected EOA, not the Safe).
  - [ ] d. **PT-USDC** — if Pendle has a Sepolia testnet UI, mint there; otherwise leave as a mock and document the substitution in `docs/BOUNTY_PROOF.md`.
  - [x] e. Confirmed token balances on Safe Assets Dashboard: USDC (40) and ETH (0.05) verified present.
- [x] 3. Pin all Sepolia token addresses in `.env` — already present:
   ```
   WETH_ADDRESS=0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14
   USDC_ADDRESS=0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238
   STETH_ADDRESS=0xaa13a290ebf492a0614050eb4243abaf49d79cae
   WBTC_ADDRESS=0x29f2d40b0605204364af54ec677bd022da425d03
   PT_USDC_ADDRESS=0x0000000000000000000000000000000000000000  ← still a placeholder
   ```
  - [x] Confirmed: all four token addresses present in `.env`. `PT_USDC_ADDRESS` remains zero-address placeholder — document as mock substitution in `docs/BOUNTY_PROOF.md`.

---

## 3. Deploy 2-of-3 Gnosis Safe on Sepolia (Step 5.1) ✓ COMPLETE

**Depends on:** Step 2 (need Sepolia ETH).

> **Note:** Deployed as **2-of-3** (Admin MetaMask `0xba57...` + Quant agent + Patriarch agent)
> rather than 2-of-2. Two agents can trade autonomously; Admin key can override if needed.

### What to do
- [x] 1. Open the Safe app on Sepolia (https://app.safe.global?chain=sep) and connect deployer wallet.
- [x] 2. Create Safe with three owners (Admin EOA + QUANT_ADDR + PATRIARCH_ADDR), threshold 2-of-3.
  - [x] a. Agent EOA addresses derived from `QUANT_PRIVATE_KEY` and `PATRIARCH_PRIVATE_KEY` in `.env`.
  - [x] b. Deployed and confirmed on Sepolia. Safe address: `0xd42C17165aC8A2C69f085FAb5daf8939f983eB21`.
- [x] 3. Funded the Safe:
  - [x] a. Sent **0.05 Sepolia ETH** from MetaMask to Safe for gas headroom.
  - [x] b. Sent **40 USDC** from Circle faucet directly to Safe.
- [x] 4. Pinned in `.env`: `SAFE_ADDRESS=0xd42C17165aC8A2C69f085FAb5daf8939f983eB21`
- [x] 5. Confirmed Safe is visible on Sepolia Etherscan and indexed in Safe Assets Dashboard.

---

## 4. Deploy ArbiterThrottleHook on Sepolia (Step 4.5) ✱ Uniswap Elite-1

**Depends on:** Step 2 (need Sepolia ETH), Foundry installed.

This is the hardest deployment task — the hook address must have specific permission bits
set in its low 14 bits (CREATE2 salt mining required).

### What to do
- [x] 1. Install Foundry.
  - [x] a. Downloaded `foundry_v1.7.0_win32_amd64.zip` from GitHub releases → extracted to `C:\foundry`.
  - [x] b. Added `C:\foundry` to `PATH` (user-level env var set permanently).
  - [x] c. Confirmed: `forge --version` → `forge Version: 1.6.0-v1.7.0` (≥ 0.2.0 ✓).
- [x] 2. Set up Foundry project at repo root.
  - [x] a. Created `foundry.toml` with `src = "contracts"`, `out = "out"`, `libs = ["lib"]`, `solc_version = "0.8.26"`, optimizer on, rpc/etherscan stanzas.
  - [x] b. Added `lib/` to `.gitignore` (`out/` and `cache/` were already present).
  - [x] c. Ran `forge init --force .` → installed `forge-std v1.16.1`.
  - [x] d. Ran `forge install Uniswap/v4-core` → installed `v4.0.0`.
  - [x] e. Ran `forge install Uniswap/v4-periphery` → installed.
  - [x] f. Ran `forge install OpenZeppelin/openzeppelin-contracts` → installed `v5.6.1`.
  - [x] g. `contracts/ArbiterThrottleHook.sol` rewritten to implement `IHooks` directly (BaseHook was removed from v4-periphery v4.0.0). `forge build` → **Compiler run successful**.
- [x] 3. Pin addresses in `.env` (Step 4.1 in roadmap):
  - [x] a. `V4_POOL_MANAGER=0x000000000004444c5dc75cb358380d2e3de08a90` — added (verify still current before deploy).
  - [x] b. `PERMIT2_ADDRESS=0x000000000022D473030F116dDEE9F6B43aC78BA3` — added (canonical cross-chain).
  - [x] c. `SEPOLIA_RPC=https://rpc.ankr.com/eth_sepolia` — added (mirrors existing `ETH_RPC_URL`; swap for Alchemy/Infura endpoint for reliability under load).
  - [x] d. `UNIVERSAL_ROUTER_ADDRESS=0x66a9893cc07d91d95644aedd05d03f95e1dba8af` — confirmed (Uniswap v4 Sepolia).
  - [x] e. `ETHERSCAN_API_KEY` — add from etherscan.io/myapikey.
- [x] 4. `script/HookMiner.s.sol` written and run ✓. Salt mined in 3831 iterations.
   - `HOOK_SALT=0x0000000000000000000000000000000000000000000000000000000000000ef7`
   - `ARBITER_THROTTLE_HOOK=0x4Fb70855Af455680075d059AD216a01A161800C0`
- [x] 5. `script/DeployThrottleHook.s.sol` written and deployed ✓.
   - Deployed: `0x4Fb70855Af455680075d059AD216a01A161800C0`
   - Tx: `0x082752540ff417181607fd41d64e54a69306958aee05d6b2304c86e9c22fa67a`
   - Block: 10775727 (Sepolia)
- [x] 6. `ARBITER_THROTTLE_HOOK=0x4Fb70855Af455680075d059AD216a01A161800C0` pinned in `.env`.
- [x] 7. Permission bits verified: `0x4Fb70855...C0 & 0x3FFF = 0xC0 = 192` ✓. Contract verified on Sepolia Etherscan.

---

## 5. Deploy ArbiterReceipt SBT Contract (Step 6.7)

**Depends on:** Step 2 (Sepolia ETH), Foundry installed ✓, Step 4 (Foundry project initialized ✓).

The contract already exists at `contracts/ArbiterReceipt.sol`. Deploy script written at `script/DeployArbiterReceipt.s.sol`.

### What to do
- [x] 1. `script/DeployArbiterReceipt.s.sol` written ✓.
- [x] 2. Deployed ✓.
   - Address: `0x47D6414fbf582141D4Ce54C3544C14A6057D5a04`
   - Chain: Sepolia (11155111)
   - Contract verified on Sepolia Etherscan ✓
- [x] 3. `ARBITER_RECEIPT_NFT=0x47D6414fbf582141D4Ce54C3544C14A6057D5a04` pinned in `.env`.

---

## 6. Enable KeeperHub Module on Safe (Step 5.2) ✓ COMPLETE

**Depends on:** Steps 3 ✓ and the KeeperHub server running (Step 7 below).

### What to do
- [x] 1. Complete Step 7 (KeeperHub server setup) first.
- [x] 2. Run:
   ```bash
   python scripts/enable_keeperhub_module.py
   ```
- [x] 3. Both `QUANT_PRIVATE_KEY` and `PATRIARCH_PRIVATE_KEY` must be set in `.env` for this to
   produce the 2-of-2 multisig that the Safe requires.
- [x] 4. Confirm on Sepolia Etherscan: the Safe's modules list now includes the KeeperHub address.
   - Module: `0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D`
   - Tx: `0x7cd80e05dbb594f70cf6439c168817eb873d9b12811c4a988049a10a01a3f30b`
   - Block: 10775996 (Sepolia)

---

## 7. KeeperHub MCP Server Setup

**Required for:** Step 5.2 (module enable), Step 5.3 (sim oracle during Patriarch eval),
and all chaos scripts involving `keeperhub_mcp_crash.sh`.

### What to do
- [x] 1. Built `scripts/keeperhub_mcp_server.py` — Python FastMCP server implementing
   `simulate_safe_tx` (real `eth_call` on Sepolia, real `fork_block`, attestor-signed)
   and `execute_safe_transaction`. No external binary needed — launched automatically
   as a stdio subprocess by `langchain_keeperhub.py`.
   - **Note:** `@keeperhub/mcp-server` npm package does not exist publicly (404). Self-built
     Python implementation using the MCP SDK (`mcp.server.fastmcp.FastMCP`) instead.
  - [x] a. Attestor keypair generated:
      - `KEEPERHUB_ATTESTOR_ADDR=0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D`
      - `KEEPERHUB_ATTESTOR_KEY` set in `.env`
- [x] 2. Set in `.env`:
   ```
   KEEPERHUB_SERVER_PATH=scripts/keeperhub_mcp_server.py
   KEEPERHUB_ATTESTOR_KEY=0x81b39e...
   KEEPERHUB_ATTESTOR_ADDR=0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D
   ```
- [x] 3. Server auto-starts via stdio — no dedicated terminal needed. `langchain_keeperhub.py`
   detects `.py` extension and spawns with `sys.executable` (the venv Python).
- [x] 4. Import verified: `from langchain_keeperhub import KeeperHubSimulateTool` → OK.
- [x] 5. Live simulation verified against Sepolia:
  - [x] a. Confirmed `fork_block=10775911` (real Sepolia block), signed response,
      attestor signature recovers to `0xf278A8c45d6cf6AECe9c0F7217Fe1bfD7b1a5C8D` ✓
  - [x] b. Mock path also signs correctly (no longer returns zero-sig / OUTSIDE_MANDATE).
  - [x] c. All 20 tests pass including `test_keeper_hub_mock`.

---

## 8. One-Time Permit2 Approvals

**Depends on:** Steps 3 ✓ and 7 (Safe deployed, KeeperHub running).

### What to do
- [x] 1. `scripts/enable_permit2.py` written ✓ — calls `Permit2.approve(token, universalRouter, maxUint160, maxUint48)` for WETH, USDC, stETH, WBTC via direct Safe `execTransaction` (EIP-712 signed by QUANT_KEY + PATRIARCH_KEY). Does NOT require KeeperHub.
- [ ] 2. Run:
   ```bash
   python scripts/enable_permit2.py
   ```

---

## 9. End-to-End Live Transaction Test (Step 5.4)

**Depends on:** Steps 1–8 all complete.

### What to do
- [ ] 1. Start all 5 daemons in separate terminals (with AXL nodes running):
   ```bash
   python quant_process.py
   python patriarch_process.py
   python execution_process.py
   python byzantine_watchdog.py
   # KeeperHub MCP server running in background
   ```
- [ ] 2. Run `python monitor_network.py` in another terminal.
- [ ] 3. Inject a scenario:
   ```bash
   python market_injector.py flash_crash_eth
   ```
- [ ] 4. Verify on Sepolia Etherscan:
  - [ ] a. Real swap from Safe → Universal Router → PoolManager (with `ArbiterThrottleHook`).
  - [ ] b. `ArbiterReceipt` SBT minted to Safe.
- [ ] 5. Run `python verify_audit.py --walk-from-head` and confirm `CHAIN VERIFIED`.

---

## 10. `docs/KEEPERHUB_FEEDBACK.md` — Real Content (Step 8.4) ✱ $250 Bounty

**This cannot be written by an AI.** The KeeperHub Builder Feedback bounty requires
friction points from *your actual integration experience* — not theoretical ones.

> ⚠️ **Integrity note:** A `docs/KEEPERHUB_FEEDBACK.md` file already exists in the repo
> (~7.9 KB, committed earlier in the sprint). Its dated friction points are speculative /
> AI-drafted and **must be replaced** with real entries from Steps 6–8 before submission.
> Treat the existing file as a scratch template, not as the deliverable.

### What to do
- [ ] 1. While working through Steps 6–8 above, log every friction point in
   `docs/KEEPERHUB_FEEDBACK.scratch.md` as you encounter them. One-liners are fine.
- [ ] 2. Day 9 morning, **overwrite** `docs/KEEPERHUB_FEEDBACK.md` with formal entries derived
   from real integration friction (the existing file content is placeholder).
- [ ] 3. Requirements: **≥3 friction-point sections, ≥4 KB total**, each with:
  - Date encountered
  - Affected component
  - Reproduction steps
  - Expected vs actual
  - Workaround / suggested fix
- [ ] 4. Submit via KeeperHub's bounty form (check their Discord/docs for the Typeform link).
- [ ] 5. Verify: `python scripts/check_bounty_compliance.py` shows `keeperhub.builder_feedback ✓`.

---

## 11. Public Verifier Page Deployment (Step 8.2) ✱ Elite-5b

The page was built in `monitor/public_verifier/`. It needs to be **deployed** to Vercel
(or equivalent) so the QR code resolves to a real public URL.

### What to do
- [ ] 1. Create a Vercel account if you don't have one.
  - [ ] a. Go to https://vercel.com/signup → sign in with GitHub.
  - [ ] b. Install the CLI globally: `npm install -g vercel` → confirm `vercel --version`.
  - [ ] c. Authenticate the CLI: `vercel login` → enter the email tied to your account → click the verification link.
- [ ] 2. Deploy:
   ```bash
   cd monitor/public_verifier/
   vercel --prod
   ```
  - [ ] a. On first run, accept the project name `arbiter-public-verifier`, personal scope, no link to existing project.
  - [ ] b. Copy the `https://arbiter-public-verifier-<hash>.vercel.app` URL from CLI output.
- [ ] 3. Pin the public URL:
  - [ ] a. Add to `.env`: `PUBLIC_VERIFIER_URL=https://arbiter-public-verifier-<hash>.vercel.app`.
  - [ ] b. Confirm `monitor_network.py` reads `PUBLIC_VERIFIER_URL` from env; update if it hard-codes a placeholder.
- [ ] 4. Confirm: scanning the QR on a separate device shows `CHAIN VERIFIED` with real receipt data.

---

## 12. `docs/BOUNTY_PROOF.md` (Step 9.1)

This document lists real on-chain artifacts — tx hashes, contract addresses, NFT token URIs.
It can only be written **after** Steps 3–9 produce real on-chain state.

### What to populate (template)
```markdown
# Bounty Proof — Arbiter Capital

## 0G ($15k)
- LLMContext tx hashes (≥6): 0x..., 0x...
- DecisionReceipt tx hashes (≥3): 0x..., 0x...
- replay_decision.py output: [paste]
- Audit chain length: N receipts
- Public verifier URL: https://...

## Gensyn ($5k)
- AXL node IDs: Quant_Node_A, Patriarch_Node_B, Execution_Node_P3, KeeperHub_Sim_P4, Adversary_Node_Z
- AttackRejection receipt tx hashes (≥6): 0x...
- network.py _assert_demo_transport code: [link to line]

## Uniswap ($5k)
- ArbiterThrottleHook deployment tx: 0x...
- Etherscan verified contract: https://sepolia.etherscan.io/address/0x...
- Swap tx routed through hook: 0x...

## KeeperHub Best Use ($4.5k)
- Module-enable tx: 0x...
- Sim oracle invocations count: N (≥3)
- langchain_keeperhub.py: [link]
- F2 evidence: [paste tool import test output]

## KeeperHub Builder Feedback ($500)
- KEEPERHUB_FEEDBACK.md URL: [link]
- Submission timestamp: 2026-05-0X HH:MM UTC
```

---

## 13. Dress Rehearsal (Step 8.5)

**Depends on:** All steps above complete and working.

### What to do
- [ ] 1. Run `python scripts/demo_run.py` three times in a row with a fresh `state/` directory.
- [ ] 2. All three must complete in 4–5 minutes without manual intervention.
- [ ] 3. Record one run with OBS as insurance footage.
- [ ] 4. Verify:
  - [ ] a. Watchdog rejection pane flashes red 6 times.
  - [ ] b. QR scan on a separate device shows `CHAIN VERIFIED`.
  - [ ] c. `replay_decision.py` shows `parsed_hash` match on at least one LLM call.
  - [ ] d. `python scripts/check_bounty_compliance.py` exits 0.

---

## 14. Final Submission (Step 9.3)

### What to submit on ETHGlobal portal
- [ ] GitHub repo URL
- [ ] Demo video URL (3 min, OBS recording from dress rehearsal)
- [ ] `SAFE_ADDRESS` (Sepolia)
- [ ] Public verifier URL
- [ ] List of 0G receipt tx hashes (≥6 LLMContext, ≥6 AttackRejection, ≥3 ExecutionReceipt)
- [ ] List of Sepolia execution tx hashes (≥3 swaps)
- [ ] `ArbiterThrottleHook` deployment tx + Etherscan verification link
- [ ] `ArbiterReceipt` SBT contract + ≥3 minted token URIs
- [ ] `docs/BOUNTY_PROOF.md` committed and linked

---

## Summary: Dependency Order

```
Step 1  (AXL nodes)               ✓ DONE
Step 2  (Funding)                 ✓ DONE (WETH/stETH/WBTC wrapping still needed)
Step 3  (Deploy Safe)             ✓ DONE — 0xd42C17165aC8A2C69f085FAb5daf8939f983eB21
Step 4  (Deploy ThrottleHook)     ✓ DONE — 0x4Fb70855Af455680075d059AD216a01A161800C0
Step 5  (Deploy ArbiterReceipt)   ✓ DONE — 0x47D6414fbf582141D4Ce54C3544C14A6057D5a04
Step 8  (Permit2 approvals)       script written, needs WETH/stETH/WBTC in Safe first

Step 7  (KeeperHub server)        ✓ DONE — scripts/keeperhub_mcp_server.py, attestor 0xf278A8c4...

Step 6  (Enable KeeperHub Module on Safe)  ✓ DONE — 0x7cd80e05...f30b, block 10775996
  └→ Step 8  (Run Permit2 approvals)  ← NEXT BLOCKER (needs WETH/stETH/WBTC in Safe first)
  └→ Step 9  (E2E live tx)
       └→ Step 10 (Real KEEPERHUB_FEEDBACK.md)
       └→ Step 11 (Deploy public verifier to Vercel)
       └→ Step 12 (Write BOUNTY_PROOF.md with real tx hashes)
       └→ Step 13 (Dress rehearsal x3)
       └→ Step 14 (Submit)
```

## Code Still Needed (AI can write, but blocked on infra)

| Item | File | Status |
|---|---|---|
| `scripts/enable_permit2.py` | `scripts/enable_permit2.py` | **Done** ✓ — EIP-712 Safe tx, direct execTransaction |
| ArbiterThrottleHook Solidity contract | `contracts/ArbiterThrottleHook.sol` | **Done** ✓ — compiles against v4-core v4.0.0 |
| ArbiterReceipt Solidity contract | `contracts/ArbiterReceipt.sol` | **Done** ✓ — deployed `0x47D6414f...5a04` |
| Foundry project scaffolding | `foundry.toml` (repo root) | **Done** ✓ |
| `script/HookMiner.s.sol` | `script/HookMiner.s.sol` | **Done** ✓ — run `forge script` to mine salt |
| `script/DeployThrottleHook.s.sol` | `script/DeployThrottleHook.s.sol` | **Done** ✓ — deployed `0x4Fb70855...00C0` |
| `script/DeployArbiterReceipt.s.sol` | `script/DeployArbiterReceipt.s.sol` | **Done** ✓ — deployed `0x47D6414f...5a04` |
| `docs/BOUNTY_PROOF.md` | Not yet created | Needs real tx hashes |
| `docs/AUDIT_REPRODUCE.md` | Not yet created | Can be written anytime |
| `docs/SECURITY.md` | Not yet created | Can be written anytime |
