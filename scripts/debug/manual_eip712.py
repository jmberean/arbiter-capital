from eth_utils import keccak, to_checksum_address
from eth_abi import encode as abi_encode
import json

def _hex_to_bytes32(h):
    if not h: return b"\x00" * 32
    raw = h[2:] if h.startswith("0x") else h
    return bytes.fromhex(raw.rjust(64, "0"))

def _resolve_address(symbol):
    ADDRESS_BY_SYMBOL = {
        "WETH":   "0xfFf9976782d46CC05630D1f6eBab18b2324d6B14",
        "USDC":   "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    }
    addr = ADDRESS_BY_SYMBOL.get(symbol, "0x" + "00" * 20)
    return to_checksum_address(addr)

payload = {
    "proposal_id": "20231101-001_v2",
    "iteration": 1,
    "target_protocol": "Uniswap_V4",
    "v4_hook_required": "",
    "action": "SWAP",
    "asset_in": "ETH",
    "asset_out": "USDC",
    "amount_in_units": 10000000000000000000,
    "min_amount_out_units": 0,
    "deadline_unix": 1700000000,
    "projected_apy_bps": 400,
    "risk_score_bps": 200,
    "quant_analysis_hash": "0x9eb154e986895c22cec60cae44ebff80eedd141ff4905a8e5763aa4c760a31e1",
    "market_snapshot_hash": "0x7855e9ccc4ddd262bf65e8a990e6e65c462e3e051584d5d0d689ddb876c35604",
    "llm_context_hash": "0x03ecabc918be4076382fa790c75212699b6b89775952f16f0f7317072f5cc6fc",
    "safe_nonce": 8
}

PROPOSAL_TYPE_STR = (
    "Proposal(string proposal_id,uint16 iteration,string target_protocol,"
    "string v4_hook_required,string action,address asset_in,address asset_out,"
    "uint256 amount_in_units,uint256 min_amount_out_units,uint64 deadline_unix,"
    "uint32 projected_apy_bps,uint16 risk_score_bps,bytes32 quant_analysis_hash,"
    "bytes32 market_snapshot_hash,bytes32 llm_context_hash,uint256 safe_nonce)"
)
PROPOSAL_TYPEHASH = keccak(text=PROPOSAL_TYPE_STR)

def struct_hash(p):
    return keccak(abi_encode(
        ["bytes32", "bytes32", "uint256", "bytes32", "bytes32", "bytes32", "address", "address",
         "uint256", "uint256", "uint256", "uint32", "uint16", "bytes32", "bytes32", "bytes32", "uint256"],
        [
            PROPOSAL_TYPEHASH,
            keccak(text=p["proposal_id"]),
            p["iteration"],
            keccak(text=p["target_protocol"]),
            keccak(text=p["v4_hook_required"]),
            keccak(text=p["action"]),
            _resolve_address(p["asset_in"]),
            _resolve_address(p["asset_out"]),
            p["amount_in_units"],
            p["min_amount_out_units"],
            p["deadline_unix"],
            p["projected_apy_bps"],
            p["risk_score_bps"],
            _hex_to_bytes32(p["quant_analysis_hash"]),
            _hex_to_bytes32(p["market_snapshot_hash"]),
            _hex_to_bytes32(p["llm_context_hash"]),
            p["safe_nonce"]
        ]
    ))

s_hash = struct_hash(payload)
print(f"Manual structHash: 0x{s_hash.hex()}")

# Now try different domain separators
DOMAIN_TYPEHASH = keccak(text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")

def domain_separator(name, version, chain_id, contract):
    return keccak(abi_encode(
        ["bytes32", "bytes32", "bytes32", "uint256", "address"],
        [
            DOMAIN_TYPEHASH,
            keccak(text=name),
            keccak(text=version),
            chain_id,
            to_checksum_address(contract)
        ]
    ))

def eip712_digest(name, version, chain_id, contract, s_hash):
    ds = domain_separator(name, version, chain_id, contract)
    return keccak(b"\x19\x01" + ds + s_hash)

digest = eip712_digest("ArbiterCapital", "1", 1, "0x0000000000000000000000000000000000000000", s_hash)
print(f"Manual Digest (chainId=1, contract=0): 0x{digest.hex()}")

digest2 = eip712_digest("ArbiterCapital", "1", 11155111, "0x0000000000000000000000000000000000000000", s_hash)
print(f"Manual Digest (chainId=11155111, contract=0): 0x{digest2.hex()}")

# Try minimal domain separator (SafeTreasury style)
DOMAIN_TYPEHASH_MINIMAL = keccak(text="EIP712Domain(uint256 chainId,address verifyingContract)")

def domain_separator_minimal(chain_id, contract):
    return keccak(abi_encode(
        ["bytes32", "uint256", "address"],
        [
            DOMAIN_TYPEHASH_MINIMAL,
            chain_id,
            to_checksum_address(contract)
        ]
    ))

def eip712_digest_minimal(chain_id, contract, s_hash):
    ds = domain_separator_minimal(chain_id, contract)
    return keccak(b"\x19\x01" + ds + s_hash)

print("\n--- Minimal Domain ---")
digest_m1 = eip712_digest_minimal(1, "0x0000000000000000000000000000000000000000", s_hash)
print(f"Minimal Digest (chainId=1, contract=0): 0x{digest_m1.hex()}")

digest_m2 = eip712_digest_minimal(11155111, "0x0000000000000000000000000000000000000000", s_hash)
print(f"Minimal Digest (chainId=11155111, contract=0): 0x{digest_m2.hex()}")

digest_m3 = eip712_digest_minimal(1, "0xd42C17165aC8A2C69f085FAb5daf8939f983eB21", s_hash)
print(f"Minimal Digest (chainId=1, contract=real): 0x{digest_m3.hex()}")

print(f"Target Hash: 0x59e6aaa6ae3bfa67288fb16bdce00fa4a4cb1bfb49b67b0c5efcbffabaebfc2d")
