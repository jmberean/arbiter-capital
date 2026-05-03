from eth_utils import keccak, to_checksum_address
from eth_abi import encode as abi_encode
from eth_account.messages import encode_typed_data

PROPOSAL_TYPE_STR = (
    "Proposal(string proposal_id,uint16 iteration,string target_protocol,"
    "string v4_hook_required,string action,address asset_in,address asset_out,"
    "uint256 amount_in_units,uint256 min_amount_out_units,uint64 deadline_unix,"
    "uint32 projected_apy_bps,uint16 risk_score_bps,bytes32 quant_analysis_hash,"
    "bytes32 market_snapshot_hash,bytes32 llm_context_hash,uint256 safe_nonce)"
)
PROPOSAL_TYPEHASH = keccak(text=PROPOSAL_TYPE_STR)

msg = {
    'proposal_id': '20231101-001', 
    'iteration': 1, 
    'target_protocol': 'Uniswap_V4', 
    'v4_hook_required': '', 
    'action': 'SWAP', 
    'asset_in': '0x0000000000000000000000000000000000000000', 
    'asset_out': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238', 
    'amount_in_units': 10000000000000000000, 
    'min_amount_out_units': 0, 
    'deadline_unix': 1700000000, 
    'projected_apy_bps': 400, 
    'risk_score_bps': 200, 
    'quant_analysis_hash': bytes.fromhex('9eb154e986895c22cec60cae44ebff80eedd141ff4905a8e5763aa4c760a31e1'),
    'market_snapshot_hash': bytes.fromhex('bd2576f24085989d347e0cd1afefd001b22f3b0b8805d2e52e525c1141d079f4'),
    'llm_context_hash': bytes.fromhex('4b58712f08889a9583ab7fd24b190e943bb6cd3ed8e85fd841b3c0056a2f06aa'),
    'safe_nonce': 8
}

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
            to_checksum_address(p["asset_in"]),
            to_checksum_address(p["asset_out"]),
            p["amount_in_units"],
            p["min_amount_out_units"],
            p["deadline_unix"],
            p["projected_apy_bps"],
            p["risk_score_bps"],
            p["quant_analysis_hash"],
            p["market_snapshot_hash"],
            p["llm_context_hash"],
            p["safe_nonce"]
        ]
    ))

s_hash = struct_hash(msg)
print(f"Computed structHash: 0x{s_hash.hex()}")

target = "0x7cd5bba372716c59b37184cceb1509f9fcc5701ac87e0cd714563d27d2199df9"
print(f"Target Hash:         {target}")

if s_hash.hex() == target[2:]:
    print("SUCCESS: Struct hash matches target!")
else:
    print("FAILURE: Struct hash mismatch.")

# Now try with Domain
DOMAIN_TYPEHASH = keccak(text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
ds = keccak(abi_encode(
    ["bytes32", "bytes32", "bytes32", "uint256", "address"],
    [
        DOMAIN_TYPEHASH,
        keccak(text="ArbiterCapital"),
        keccak(text="1"),
        1,
        to_checksum_address("0x0000000000000000000000000000000000000000")
    ]
))
digest = keccak(b"\x19\x01" + ds + s_hash)
print(f"Full EIP-712 Digest: 0x{digest.hex()}")

if digest.hex() == target[2:]:
    print("SUCCESS: Full digest matches target!")
