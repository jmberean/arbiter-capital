# Manual Action Required — Arbiter Capital Go-Live Checklist

**As of:** 2026-04-29
**Deadline:** 2026-05-06 (7 days)
**Why this doc exists:** Everything below requires keys, wallets, running infrastructure, or
real-world experience that requires manual action.
Work through this list in order — later items depend on earlier ones.

---

## 1. Gensyn AXL — Live Node Deployment (Step 0.4) ✱ BOUNTY DISQUALIFIER

**Risk level: CRITICAL.** Without real AXL nodes the Gensyn bounty is void by definition.
The code already enforces this: `DEMO_MODE=1` without `AXL_NODE_URL_*` exits with code 1.

### What to do
1. Read the live Gensyn AXL docs (URL may have changed — verify at hackathon time).
2. Install the AXL node binary on your demo machine.
3. Run `bash scripts/setup_axl.sh` — this launches 5 nodes on ports 9001–9005.
   The exact CLI flags in that script are **intended** not **confirmed** — verify each flag
   against the live docs before running.
4. Add to `.env`:
   ```
   AXL_NODE_URL_QUANT=http://127.0.0.1:9001
   AXL_NODE_URL_PATRIARCH=http://127.0.0.1:9002
   AXL_NODE_URL_EXEC=http://127.0.0.1:9003
   AXL_NODE_URL_KEEPERHUB=http://127.0.0.1:9004
   AXL_NODE_URL_WATCHDOG=http://127.0.0.1:9005
   DEMO_MODE=1
   ```
5. Confirm: `DEMO_MODE=1 python quant_process.py` (with `AXL_NODE_URL_QUANT` **unset**) exits
   with code 1 and prints the compliance error. Then set the var and confirm it starts cleanly.
6. Verify `monitor_network.py` shows ≥4 distinct senders within 60 seconds of a full run.

**Acceptance:** `axl-node status` (or equivalent) shows 5 healthy nodes meshed together.

---

## 2. Sepolia ETH + Test Token Funding

Before any on-chain deployment, your deployer wallet needs gas money and the Safe needs
test tokens.

### What to do
1. Get Sepolia ETH for the deployer key (`EXECUTOR_PRIVATE_KEY` or a separate deployer):
   - Alchemy Sepolia faucet: https://sepoliafaucet.com
   - Infura faucet: https://www.infura.io/faucet/sepolia
   - Need ≥0.5 Sepolia ETH (hook deploy + Safe deploy + execution txs).
2. Get Sepolia test tokens for the Safe (after the Safe is deployed in Step 3):
   - **WETH:** wrap Sepolia ETH via `WETH.deposit{value: 0.1 ether}()`.
   - **USDC:** Aave Sepolia faucet or Circle's testnet tap.
   - **stETH / WBTC:** use Aave's Sepolia market faucet UI.
   - **PT-USDC:** mint via the Pendle Sepolia testnet UI (if available), otherwise use a mock.
3. Pin all Sepolia token addresses in `.env` (WETH, USDC, stETH, WBTC, PT-USDC).

---

## 3. Deploy 2-of-2 Gnosis Safe on Sepolia (Step 5.1)

**Depends on:** Step 2 (need Sepolia ETH).

### What to do
1. Go to [https://app.safe.global?chain=sep](https://app.safe.global?chain=sep).
2. Create a new Safe with:
   - **Owners:** `[QUANT_ADDR, PATRIARCH_ADDR]` (derive these from your private keys via
     `python -c "from core.identity import QUANT_ADDR, PATRIARCH_ADDR; print(QUANT_ADDR, PATRIARCH_ADDR)"`)
   - **Threshold:** 2
3. Fund the Safe with amounts from Step 2.
4. Pin in `.env`:
   ```
   SAFE_ADDRESS=0x<deployed Safe address>
   ```
5. Confirm the Safe is visible on Sepolia Etherscan.

---

## 4. Deploy ArbiterThrottleHook on Sepolia (Step 4.5) ✱ Uniswap Elite-1

**Depends on:** Step 2 (need Sepolia ETH), Foundry installed.

This is the hardest deployment task — the hook address must have specific permission bits
set in its low 14 bits (CREATE2 salt mining required).

### What to do
1. Install Foundry if not already installed: `curl -L https://foundry.paradigm.xyz | bash && foundryup`
2. Install hook dependencies:
   ```bash
   cd hooks/
   forge install Uniswap/v4-core
   forge install Uniswap/v4-periphery
   forge install OpenZeppelin/openzeppelin-contracts
   ```
3. Pin addresses in `.env` first (Step 4.1 in roadmap):
   - `UNIVERSAL_ROUTER_ADDRESS` — from Uniswap's official Sepolia deployment registry.
   - `V4_POOL_MANAGER=0x000000000004444c5dc75cb358380d2e3de08a90` (verify this is current).
   - `PERMIT2_ADDRESS=0x000000000022D473030F116dDEE9F6B43aC78BA3` (verify).
   - `SEPOLIA_RPC` — your Alchemy/Infura Sepolia RPC URL.
4. Mine the CREATE2 salt (can take 5–30 minutes):
   ```bash
   forge script hooks/HookMiner.s.sol --rpc-url $SEPOLIA_RPC -vvv
   ```
5. Deploy:
   ```bash
   forge script script/DeployThrottleHook.s.sol \
       --rpc-url $SEPOLIA_RPC \
       --private-key $DEPLOYER_KEY \
       --broadcast \
       --verify
   ```
6. Pin in `.env`:
   ```
   ARBITER_THROTTLE_HOOK=0x<deployed address>
   ```
7. Verify the hook address has correct permission bits:
   ```bash
   cast call $V4_POOL_MANAGER "isValidHookAddress(address,uint24)" $ARBITER_THROTTLE_HOOK 3000
   ```

**Warning:** Salt mining can fail if your target permission bits don't match the available
address space. The Foundry `HookMiner.s.sol` script handles this but it needs to be
correct — verify the permission flags in `ArbiterThrottleHook.sol` match what
`execution/firewall.py::validate_hook_address` expects.

---

## 5. Deploy ArbiterReceipt SBT Contract (Step 6.7)

**Depends on:** Step 2 (Sepolia ETH), Foundry installed.

### What to do
```bash
forge script script/DeployArbiterReceipt.s.sol \
    --rpc-url $SEPOLIA_RPC \
    --private-key $DEPLOYER_KEY \
    --broadcast \
    --verify
```
Pin in `.env`:
```
ARBITER_RECEIPT_NFT=0x<deployed address>
```

---

## 6. Enable KeeperHub Module on Safe (Step 5.2)

**Depends on:** Steps 3 and the KeeperHub server running (Step 7 below).

The script `scripts/enable_keeperhub_module.py` was written in the last commit.
You still need to **run it** with real keys against the live Safe.

### What to do
1. Set up the KeeperHub MCP server (Step 7).
2. Run:
   ```bash
   python scripts/enable_keeperhub_module.py
   ```
3. Both `QUANT_PRIVATE_KEY` and `PATRIARCH_PRIVATE_KEY` must be set in `.env` for this to
   produce the 2-of-2 multisig that the Safe requires.
4. Confirm on Sepolia Etherscan: the Safe's modules list now includes the KeeperHub address.

---

## 7. KeeperHub MCP Server Setup

**Required for:** Step 5.2 (module enable), Step 5.3 (sim oracle during Patriarch eval),
and all chaos scripts involving `keeperhub_mcp_crash.sh`.

### What to do
1. Follow KeeperHub's installation docs to get the MCP server binary.
2. Set in `.env`:
   ```
   KEEPERHUB_SERVER_PATH=/path/to/keeperhub-mcp-server
   KEEPERHUB_ATTESTOR_KEY=0x<KeeperHub attestor private key>
   ```
3. Verify the bridge works:
   ```bash
   python -c "from langchain_keeperhub import KeeperHubSimulateTool; print('OK')"
   ```
4. Verify simulation calls work against the deployed Safe (Step 3 must be done first).

---

## 8. One-Time Permit2 Approvals

**Depends on:** Steps 3 and 7 (Safe deployed, KeeperHub running).

The roadmap notes: "Day 6 includes one-time `enable_permit2.py`." This script approves
Permit2 to spend the Safe's tokens on behalf of the Universal Router.

### What to do
```bash
python scripts/enable_permit2.py
```
This must be run once before any live swap can succeed. If the script doesn't exist yet,
it needs to be created — it should call `Permit2.approve(token, spender, amount, expiry)`
for each asset (WETH, USDC, stETH, WBTC, PT-USDC).

---

## 9. End-to-End Live Transaction Test (Step 5.4)

**Depends on:** Steps 1–8 all complete.

### What to do
1. Start all 5 daemons in separate terminals (with AXL nodes running):
   ```bash
   python quant_process.py
   python patriarch_process.py
   python execution_process.py
   python byzantine_watchdog.py
   # KeeperHub MCP server running in background
   ```
2. Run `python monitor/monitor_network.py` in another terminal.
3. Inject a scenario:
   ```bash
   python market_injector.py flash_crash_eth
   ```
4. Verify on Sepolia Etherscan:
   - Real swap from Safe → Universal Router → PoolManager (with `ArbiterThrottleHook`).
   - `ArbiterReceipt` SBT minted to Safe.
5. Run `python verify_audit.py --walk-from-head` and confirm `CHAIN VERIFIED`.

---

## 10. `docs/KEEPERHUB_FEEDBACK.md` — Real Content (Step 8.4) ✱ $250 Bounty

**This cannot be written by an AI.** The KeeperHub Builder Feedback bounty requires
friction points from *your actual integration experience* — not theoretical ones.

### What to do
1. While working through Steps 6–8 above, log every friction point in
   `docs/KEEPERHUB_FEEDBACK.scratch.md` as you encounter them. One-liners are fine.
2. Day 9 morning, expand into formal entries in `docs/KEEPERHUB_FEEDBACK.md`.
3. Requirements: **≥3 friction-point sections, ≥4 KB total**, each with:
   - Date encountered
   - Affected component
   - Reproduction steps
   - Expected vs actual
   - Workaround / suggested fix
4. Submit via KeeperHub's bounty form (check their Discord/docs for the Typeform link).
5. Verify: `python scripts/check_bounty_compliance.py` shows `keeperhub.builder_feedback ✓`.

---

## 11. Public Verifier Page Deployment (Step 8.2) ✱ Elite-5b

The page was built in `monitor/public_verifier/`. It needs to be **deployed** to Vercel
(or equivalent) so the QR code resolves to a real public URL.

### What to do
1. Create a Vercel account if you don't have one.
2. Deploy:
   ```bash
   cd monitor/public_verifier/
   vercel --prod
   ```
3. Pin the public URL so the QR code in `monitor_network.py` points to it.
4. Confirm: scanning the QR on a separate device shows `CHAIN VERIFIED` with real receipt data.

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
1. Run `python scripts/demo_run.py` three times in a row with a fresh `state/` directory.
2. All three must complete in 4–5 minutes without manual intervention.
3. Record one run with OBS as insurance footage.
4. Verify:
   - Watchdog rejection pane flashes red 6 times.
   - QR scan on a separate device shows `CHAIN VERIFIED`.
   - `replay_decision.py` shows `parsed_hash` match on at least one LLM call.
   - `python scripts/check_bounty_compliance.py` exits 0.

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
Step 2 (Funding)
  └→ Step 3 (Deploy Safe)
       └→ Step 8 (Permit2 approvals)
  └→ Step 4 (Deploy ThrottleHook)
  └→ Step 5 (Deploy SBT contract)

Step 7 (KeeperHub server setup)
  └→ Step 6 (Enable KeeperHub Module on Safe)  ← also needs Step 3

Step 1 (AXL nodes)  ← independent, do first

Steps 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 → Step 9 (E2E live tx)
  └→ Step 10 (Write KEEPERHUB_FEEDBACK.md with real friction)
  └→ Step 11 (Deploy public verifier)
  └→ Step 12 (Write BOUNTY_PROOF.md with real tx hashes)
  └→ Step 13 (Dress rehearsal)
  └→ Step 14 (Submit)
```

## Code Still Needed (AI can write, but blocked on infra)

These are code gaps that have not yet been written or may be incomplete:

| Item | File | Blocked on |
|---|---|---|
| `scripts/enable_permit2.py` | Not yet created | Safe address needed |
| ArbiterThrottleHook Solidity contract | `hooks/ArbiterThrottleHook.sol` | Must verify permission bit spec against actual v4-core |
| `hooks/HookMiner.s.sol` | Not yet created | Needs permission flags from above |
| `script/DeployThrottleHook.s.sol` | Not yet created | Needs hook contract |
| `docs/BOUNTY_PROOF.md` | Not yet created | Needs real tx hashes |
| `docs/AUDIT_REPRODUCE.md` | Not yet created | Can be written anytime |
| `docs/SECURITY.md` | Not yet created | Can be written anytime |

Flag the items in the last two rows to me and I can write them now.
