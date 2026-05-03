"""
Cryptographic primitives for Arbiter Capital.

Three classes of digests are produced here:

  1. proposal_eip712_digest — EIP-712 typed-data digest of a Proposal.
  2. bundle_hash             — keccak(proposal_hash || safe_tx_hash) for ConsensusBundle.
  3. sim_result_digest       — KeeperHub attestor signs this over a SimulationResult.

Every signature in the system is one of these three forms. The defenders only
trust signatures that recover to a registered SAFE_OWNER (consensus path) or
ATTESTOR (advisory path) — see core/identity.py.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address

DOMAIN_NAME = "ArbiterCapital"
DOMAIN_VERSION = "1"

PROPOSAL_TYPES = {
    "Proposal": [
        {"name": "proposal_id",          "type": "string"},
        {"name": "iteration",            "type": "uint16"},
        {"name": "target_protocol",      "type": "string"},
        {"name": "v4_hook_required",     "type": "string"},
        {"name": "action",               "type": "string"},
        {"name": "asset_in",             "type": "address"},
        {"name": "asset_out",            "type": "address"},
        {"name": "amount_in_units",      "type": "uint256"},
        {"name": "min_amount_out_units", "type": "uint256"},
        {"name": "deadline_unix",        "type": "uint64"},
        {"name": "projected_apy_bps",    "type": "uint32"},
        {"name": "risk_score_bps",       "type": "uint16"},
        {"name": "quant_analysis_hash",  "type": "bytes32"},
        {"name": "market_snapshot_hash", "type": "bytes32"},
        {"name": "llm_context_hash",     "type": "bytes32"},
        {"name": "safe_nonce",           "type": "uint256"},
    ]
}


def _normalize_message(p: Any) -> dict:
    """Accept either a Proposal instance or a pre-built dict and produce the
    EIP-712-shaped dict expected by encode_typed_data."""
    if hasattr(p, "eip712_message"):
        return p.eip712_message()
    if isinstance(p, Mapping):
        return dict(p)
    raise TypeError(f"Cannot derive EIP-712 message from {type(p).__name__}")


def proposal_eip712_digest(p: Any, verifying_contract: str, chain_id: int) -> bytes:
    """Return the 32-byte EIP-712 digest for a Proposal.

    `p` may be a Proposal instance (preferred — uses .eip712_message()) or a
    pre-built dict already conforming to PROPOSAL_TYPES.
    """
    msg = _normalize_message(p)
    
    # We use full_message to ensure the domain is correctly incorporated.
    # eth_account 0.13.7 needs explicit type definitions for the domain.
    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Proposal": PROPOSAL_TYPES["Proposal"]
    }
    
    domain = {
        "name": DOMAIN_NAME,
        "version": DOMAIN_VERSION,
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


def bundle_hash(proposal_hash: bytes, safe_tx_hash: bytes) -> bytes:
    """ConsensusBundle digest: keccak(proposal_hash || safe_tx_hash)."""
    if len(proposal_hash) != 32 or len(safe_tx_hash) != 32:
        raise ValueError("bundle_hash inputs must be 32 bytes each")
    return keccak(proposal_hash + safe_tx_hash)


def sim_result_digest(proposal_id: str, iteration: int, success: bool,
                      gas_used: int, return_data: str, fork_block: int) -> bytes:
    """Canonical digest signed by KeeperHub's attestor key over a SimulationResult.

    Mirroring is intentional: any verifier can rebuild the digest from the
    public fields and check the attestor's signature.
    """
    canonical = json.dumps({
        "proposal_id": proposal_id,
        "iteration": int(iteration),
        "success": bool(success),
        "gas_used": int(gas_used),
        "return_data": return_data or "0x",
        "fork_block": int(fork_block),
    }, sort_keys=True, separators=(",", ":")).encode()
    return keccak(canonical)


def envelope_digest(topic: str, payload: dict, timestamp: float, producer_node_id: str) -> bytes:
    """Digest signed by the producer when wrapping a payload in an AXLEnvelope."""
    canonical = json.dumps({
        "topic": topic,
        "payload": payload,
        "timestamp": float(timestamp),
        "producer_node_id": producer_node_id,
    }, sort_keys=True, separators=(",", ":")).encode()
    return keccak(canonical)


def sign_digest(digest: bytes, private_key: bytes) -> str:
    """Raw-hash sign a 32-byte digest. Returns 0x-prefixed 65-byte hex."""
    if len(digest) != 32:
        raise ValueError(f"digest must be 32 bytes, got {len(digest)}")
    return "0x" + Account.unsafe_sign_hash(digest, private_key).signature.hex()


def recover_signer(digest: bytes, sig_hex: str) -> str:
    """Recover the checksummed signer address from a raw-hash signature."""
    sig = sig_hex if sig_hex.startswith("0x") else "0x" + sig_hex
    return to_checksum_address(Account._recover_hash(digest, signature=sig))
