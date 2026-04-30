from __future__ import annotations

import os
from eth_account import Account
from eth_utils import to_checksum_address

def _key(env: str) -> bytes | None:
    v = os.getenv(env)
    if not v or v.startswith("0xabc") or v == "0x" + "0" * 64:
        return None
    try:
        return bytes.fromhex(v[2:] if v.startswith("0x") else v)
    except ValueError:
        return None

QUANT_KEY      = _key("QUANT_PRIVATE_KEY")
PATRIARCH_KEY  = _key("PATRIARCH_PRIVATE_KEY")
EXECUTOR_KEY   = _key("EXECUTOR_PRIVATE_KEY")
KEEPERHUB_KEY  = _key("KEEPERHUB_ATTESTOR_KEY")     # v5: sim oracle attestor

def _addr(k): return to_checksum_address(Account.from_key(k).address) if k else None

QUANT_ADDR     = _addr(QUANT_KEY)
PATRIARCH_ADDR = _addr(PATRIARCH_KEY)
EXECUTOR_ADDR  = _addr(EXECUTOR_KEY)
KEEPERHUB_ADDR = _addr(KEEPERHUB_KEY)

# Safe-owner registry (only these two can sign for execution)
SAFE_OWNERS: dict[str, str] = {}
if QUANT_ADDR:     SAFE_OWNERS[QUANT_ADDR]     = "Quant_Node_A"
if PATRIARCH_ADDR: SAFE_OWNERS[PATRIARCH_ADDR] = "Patriarch_Node_B"

# Attestor registry (advisory signers like KeeperHub Sim Oracle)
ATTESTORS: dict[str, str] = {}
if KEEPERHUB_ADDR: ATTESTORS[KEEPERHUB_ADDR] = "KeeperHub_Sim_Oracle"

def is_safe_owner(addr: str) -> bool:    return to_checksum_address(addr) in SAFE_OWNERS
def is_attestor(addr: str) -> bool:      return to_checksum_address(addr) in ATTESTORS
