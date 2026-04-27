from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address

DOMAIN_NAME = "ArbiterCapital"
DOMAIN_VERSION = "1"

PROPOSAL_TYPES = {
    "Proposal": [
        {"name": "proposal_id",         "type": "string"},
        {"name": "iteration",           "type": "uint16"},
        {"name": "target_protocol",     "type": "string"},
        {"name": "v4_hook_required",    "type": "string"},
        {"name": "action",              "type": "string"},
        {"name": "asset_in",            "type": "address"},
        {"name": "asset_out",           "type": "address"},
        {"name": "amount_in_units",     "type": "uint256"},
        {"name": "min_amount_out_units","type": "uint256"},
        {"name": "deadline_unix",       "type": "uint64"},
        {"name": "projected_apy_bps",   "type": "uint32"},
        {"name": "risk_score_bps",      "type": "uint16"},
        {"name": "quant_analysis_hash", "type": "bytes32"},
        {"name": "market_snapshot_hash","type": "bytes32"},
        {"name": "llm_context_hash",    "type": "bytes32"},
        {"name": "safe_nonce",          "type": "uint256"},
    ]
}

def proposal_eip712_digest(p_dict: dict, verifying_contract: str, chain_id: int) -> bytes:
    domain = {"name": DOMAIN_NAME, "version": DOMAIN_VERSION,
              "chainId": chain_id, "verifyingContract": to_checksum_address(verifying_contract)}
    return encode_typed_data(domain, PROPOSAL_TYPES, "Proposal", p_dict).body

def bundle_hash(proposal_hash: bytes, safe_tx_hash: bytes) -> bytes:
    return keccak(proposal_hash + safe_tx_hash)

def sign_digest(digest: bytes, private_key: bytes) -> str:
    return Account.unsafe_sign_hash(digest, private_key).signature.hex()

def recover_signer(digest: bytes, sig_hex: str) -> str:
    sig = sig_hex if sig_hex.startswith("0x") else "0x" + sig_hex
    return to_checksum_address(Account._recover_hash(digest, signature=sig))
