from core.crypto import proposal_eip712_digest, bundle_hash, recover_signer
from core.models import Proposal
from core.identity import QUANT_ADDR
import json

payload = {
    "proposal_id": "20231101-001_v2",
    "parent_proposal_id": None,
    "iteration": 1,
    "target_protocol": "Uniswap_V4",
    "v4_hook_required": None,
    "action": "SWAP",
    "asset_in": "ETH",
    "asset_out": "USDC",
    "asset_in_decimals": 18,
    "asset_out_decimals": 6,
    "amount_in": 10.0,
    "amount_in_units": "10000000000000000000",
    "min_amount_out_units": "USDC",
    "deadline_unix": 1700000000,
    "projected_apy": 0.04,
    "projected_apy_bps": 400,
    "risk_score_evaluation": 2.0,
    "risk_score_bps": 200,
    "quant_analysis_hash": "0x9eb154e986895c22cec60cae44ebff80eedd141ff4905a8e5763aa4c760a31e1",
    "market_snapshot_hash": "0x7855e9ccc4ddd262bf65e8a990e6e65c462e3e051584d5d0d689ddb876c35604",
    "llm_context_hash": "0x03ecabc918be4076382fa790c75212699b6b89775952f16f0f7317072f5cc6fc",
    "llm_context_0g_tx": "a2748abc51cb70b2920e5891c57d2c762686b7b1412dcc172806422127c9c022",
    "rationale": "High volatility on ETH. Rotate to stablecoin.",
    "consensus_status": "PENDING",
    "proposal_hash": "0x59e6aaa6ae3bfa67288fb16bdce00fa4a4cb1bfb49b67b0c5efcbffabaebfc2d",
    "safe_tx_hash": "0xf8ed74c527b93f3d3609b1658f019dc799dfd6fbccc4e9a0cecb806b2369620c",
    "quant_signature": "0x03ab661f5f509bafdf7de7c4ad9993379836f2264aa7948d78ef390b1d29a95d38b2e5af928e7f405c049192e34b6dab89d0ec94b65669c552be85037ff2d1a21c34294fac9f7f9604ed643787dfed76c2b4a3bb9fc1f1f548b42c2ef59ef41fa61086db4233a65e7470b6845a3a299bd6931de19ac3f5e085f50c9b87e24e67d81b",
    "patriarch_signature": None,
    "safe_nonce": 8,
    "chain_id": 1
}

proposal = Proposal(**payload)
safe_addr = "0xd42C17165aC8A2C69f085FAb5daf8939f983eB21"

safe_h = bytes.fromhex(proposal.safe_tx_hash[2:])
sig_combined = proposal.quant_signature
sig_bundle_q = sig_combined[:132]
sig_safe_q = "0x" + sig_combined[132:]

print("--- Claimed Hash Recovery ---")
claimed_p_digest = bytes.fromhex(payload["proposal_hash"][2:])
claimed_b_digest = bundle_hash(claimed_p_digest, safe_h)
recovered_claimed = recover_signer(claimed_b_digest, sig_bundle_q)
print(f"Recovered from claimed hash: {recovered_claimed}")
print(f"Expected signer:             {QUANT_ADDR}")

print("\n--- Recomputed Hash Recovery ---")
from eth_account.messages import encode_typed_data
from core.crypto import PROPOSAL_TYPES, DOMAIN_NAME, DOMAIN_VERSION
from eth_utils import to_checksum_address

def fixed_proposal_eip712_digest(p, verifying_contract, chain_id):
    msg = p.eip712_message()
    types = {
        "EIP712Domain": [
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Proposal": PROPOSAL_TYPES["Proposal"]
    }
    domain = {
        "chainId": int(chain_id),
        "verifyingContract": to_checksum_address(verifying_contract),
    }
    full_message = {
        "types": types,
        "domain": domain,
        "primaryType": "Proposal",
        "message": msg
    }
    return encode_typed_data(full_message=full_message).body

p_digest = fixed_proposal_eip712_digest(proposal, safe_addr, proposal.chain_id)
print(f"Recomputed p_digest: 0x{p_digest.hex()}")
print(f"Claimed p_digest:    {payload['proposal_hash']}")
b_digest = bundle_hash(p_digest, safe_h)
recovered = recover_signer(b_digest, sig_bundle_q)
print(f"Recovered from recomputed:   {recovered}")

print("\n--- Safe Sig Recovery ---")
recovered_safe = recover_signer(safe_h, sig_safe_q)
print(f"Recovered from safe_h:       {recovered_safe}")
print(f"Expected signer:             {QUANT_ADDR}")
