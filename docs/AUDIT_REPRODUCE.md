# Audit Reproduction Guide — Arbiter Capital

This guide explains how any third party can cryptographically verify the decisions made by the Arbiter Capital autonomous family office. Because all AI memory is persisted to the **0G Layer 1**, the system is no longer a "black box."

## 1. Prerequisites

*   **Python 3.10+**
*   **0G RPC URL** (Set in `.env` as `ZERO_G_RPC_URL`)
*   **OpenAI API Key** (Optional, required only for `replay_decision.py`)

## 2. Walk the Hash-Chained Audit Log

The most basic level of verification is walking the hash-chained audit log. Every receipt (LLM context, market snapshot, decision, execution) points to the previous receipt's 0G transaction hash.

Run the verifier:
```bash
python verify_audit.py --walk-from-head
```

**What this verifies:**
1.  **Integrity:** Each receipt's content matches its `receipt_hash`.
2.  **Continuity:** The `prev_0g_tx_hash` pointers form an unbroken chain.
3.  **Signatures:** For `DecisionReceipt` and `ExecutionReceipt`, the signatures are verified against the registered `QUANT_ADDR` and `PATRIARCH_ADDR`.

## 3. Replay AI Decisions (0G LLM Substrate)

Arbiter Capital stores the full LLM context on 0G. This includes the system prompt, the exact message array, the model ID, and the temperature.

To replay a specific decision:
1.  Find a `Proposal ID` from the monitor or a `LLMContext` transaction hash from the 0G explorer.
2.  Run the replay script:
```bash
# Replay by Proposal ID
python scripts/replay_decision.py --proposal-id <PROPOSAL_ID>

# Replay by 0G Transaction Hash
python scripts/replay_decision.py --tx <0G_TX_HASH>
```

**What this verifies:**
The script re-issues the original call to the LLM and compares the response hash.
*   **DETERMINISTIC MATCH:** The raw response matches byte-for-byte (common at temperature 0).
*   **PARSED MATCH:** The structured output (JSON schema) matches the original intent, even if the raw string differs slightly.

## 4. Verify SBT Receipts on Sepolia

Every successful trade mints an `ArbiterReceipt` (ERC-721 Soulbound Token) to the project Safe.

1.  Open the Safe address on [Sepolia Etherscan](https://sepolia.etherscan.io/address/0xd42C17165aC8A2C69f085FAb5daf8939f983eB21).
2.  Go to the "Token Holdings" or "ERC-721 Token Txns" tab.
3.  Click on an `ARDR` token and view its `tokenURI`.
4.  The URI follows the format `0g://<tx_hash>`. You can take this hash and run `python scripts/replay_decision.py --tx <tx_hash>` to see exactly why that specific NFT was minted.

## 5. Public Verifier Page

For a visual representation of the audit chain, visit:
**[Link to Public Verifier Page]** (e.g., https://arbiter-public-verifier.vercel.app)

Simply scan the QR code shown on the demo monitor to see the live, verified state of the treasury.
