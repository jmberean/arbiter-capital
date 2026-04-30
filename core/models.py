from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, List, Literal, Any
from eth_utils import keccak, to_checksum_address
import json
import time

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    SWAP = "SWAP"
    STAKE = "STAKE"
    PROVIDE_LIQUIDITY = "PROVIDE_LIQUIDITY"
    EMERGENCY_WITHDRAW = "EMERGENCY_WITHDRAW"
    BRIDGE = "BRIDGE"
    STAKE_LST = "STAKE_LST"        # ETH → stETH
    YIELD_TRADE = "YIELD_TRADE"    # Pendle PT/YT


class ConsensusStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# ---------------------------------------------------------------------------
# Decimals & address registries (Sepolia)
# ---------------------------------------------------------------------------

DECIMALS_BY_SYMBOL: Dict[str, int] = {
    "WETH": 18, "stETH": 18, "USDC": 6, "WBTC": 8,
    "PT-USDC": 6, "SOL": 9,
}

# Canonical Sepolia token addresses, mirrored in execution.uniswap_v4.router.
# Used for EIP-712 encoding (asset_in/asset_out are typed as `address`).
ADDRESS_BY_SYMBOL: Dict[str, str] = {
    "WETH":   "0xfFf9976782d46CC05630D1f6eBab18b2324d6B14",
    "USDC":   "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    "stETH":  "0x3e3FE7dBc6B4C189E7128855dD526361c49b40Af",
    "WBTC":   "0x29f2D40B0605204364af54EC677bD022dA425d03",
    "PT-USDC": "0x0000000000000000000000000000000000000000",
    "SOL":    "0x0000000000000000000000000000000000000000",
}

# Default zero-bytes32 (EIP-712 bytes32 field cannot be null)
_ZERO_BYTES32 = "0x" + "00" * 32


def _hex_to_bytes32(h: Optional[str]) -> bytes:
    """Convert a 0x-prefixed 32-byte hex string to raw bytes (32 bytes).
    Returns 32 zero bytes if h is falsy."""
    if not h:
        return b"\x00" * 32
    raw = h[2:] if h.startswith("0x") else h
    if len(raw) != 64:
        raw = raw.rjust(64, "0")
    return bytes.fromhex(raw)


def _resolve_address(symbol_or_addr: Optional[str]) -> str:
    """Resolve a symbol (e.g. 'WETH') to its Sepolia address. Pass-through if already an address."""
    if not symbol_or_addr:
        return "0x" + "00" * 20
    if symbol_or_addr.startswith("0x") and len(symbol_or_addr) == 42:
        return to_checksum_address(symbol_or_addr)
    addr = ADDRESS_BY_SYMBOL.get(symbol_or_addr, "0x" + "00" * 20)
    return to_checksum_address(addr)


# ---------------------------------------------------------------------------
# Proposal — central negotiation artifact
# ---------------------------------------------------------------------------

class Proposal(BaseModel):
    proposal_id: str = Field(..., description="Unique identifier for the proposal")
    parent_proposal_id: Optional[str] = None
    iteration: int = 1

    target_protocol: str = Field(..., description="Target DeFi protocol (e.g. Uniswap_V4)")
    v4_hook_required: Optional[str] = Field(None, description="Specific v4 hook required, if any")
    action: ActionType = Field(..., description="Action to perform")
    asset_in: str = Field(..., description="Asset to trade or use (symbol)")
    asset_out: Optional[str] = Field(None, description="Expected output asset (symbol)")

    asset_in_decimals: Optional[int] = None
    asset_out_decimals: Optional[int] = None

    amount_in: Optional[float] = None              # legacy float
    amount_in_units: Optional[str] = None          # base-units string (canonical)
    min_amount_out_units: Optional[str] = None
    deadline_unix: Optional[int] = None

    projected_apy: Optional[float] = None
    projected_apy_bps: Optional[int] = None
    risk_score_evaluation: Optional[float] = Field(None, ge=0.0, le=10.0)
    risk_score_bps: Optional[int] = None
    quant_analysis_hash: Optional[str] = None

    market_snapshot_hash: Optional[str] = None

    llm_context_hash: Optional[str] = None
    llm_context_0g_tx: Optional[str] = None

    rationale: str = Field(..., description="Detailed explanation")
    consensus_status: ConsensusStatus = Field(default=ConsensusStatus.PENDING)

    proposal_hash: Optional[str] = None
    safe_tx_hash: Optional[str] = None
    quant_signature: Optional[str] = None
    patriarch_signature: Optional[str] = None
    safe_nonce: Optional[int] = None
    chain_id: int = 11155111  # default Sepolia

    @model_validator(mode="after")
    def _populate(self):
        if self.amount_in_units is None and self.amount_in is not None:
            d = self.asset_in_decimals or DECIMALS_BY_SYMBOL.get(self.asset_in, 18)
            self.amount_in_units = str(int(self.amount_in * (10 ** d)))
            self.asset_in_decimals = d
        if self.projected_apy_bps is None and self.projected_apy is not None:
            self.projected_apy_bps = int(self.projected_apy * 100)
        if self.risk_score_bps is None and self.risk_score_evaluation is not None:
            self.risk_score_bps = int(self.risk_score_evaluation * 1000)
        if self.deadline_unix is None:
            self.deadline_unix = int(time.time()) + 600
        return self

    def eip712_message(self) -> dict:
        """Build the EIP-712 message dict matching PROPOSAL_TYPES in core.crypto.

        Resolves symbols → checksummed addresses, ActionType enum → string,
        hex strings → bytes32, and supplies sensible zero defaults so that
        encode_typed_data never receives None where a primitive is expected.
        """
        return {
            "proposal_id":         self.proposal_id,
            "iteration":           int(self.iteration or 1),
            "target_protocol":     self.target_protocol or "",
            "v4_hook_required":    self.v4_hook_required or "",
            "action":              self.action.value if isinstance(self.action, ActionType) else str(self.action),
            "asset_in":            _resolve_address(self.asset_in),
            "asset_out":           _resolve_address(self.asset_out),
            "amount_in_units":     int(self.amount_in_units or 0),
            "min_amount_out_units": int(self.min_amount_out_units or 0),
            "deadline_unix":       int(self.deadline_unix or 0),
            "projected_apy_bps":   int(self.projected_apy_bps or 0),
            "risk_score_bps":      int(self.risk_score_bps or 0),
            "quant_analysis_hash": _hex_to_bytes32(self.quant_analysis_hash),
            "market_snapshot_hash": _hex_to_bytes32(self.market_snapshot_hash),
            "llm_context_hash":    _hex_to_bytes32(self.llm_context_hash),
            "safe_nonce":          int(self.safe_nonce or 0),
        }


# ---------------------------------------------------------------------------
# Consensus
# ---------------------------------------------------------------------------

class ConsensusMessage(BaseModel):
    """Per-signer signature published on CONSENSUS_SIGNATURES topic."""
    proposal_id: str
    iteration: int = 1
    signer_id: str
    signer_address: Optional[str] = None
    role: Optional[str] = "approver"
    signature: str
    safe_tx_hash: str
    timestamp: float


class ConsensusBundle(BaseModel):
    """EIP-712 bundle: keccak(proposal_hash || safe_tx_hash) — the digest both
    Quant and Patriarch sign for non-equivocation.
    """
    proposal_id: str
    iteration: int = 1
    proposal_hash: str            # 0x-prefixed 32-byte hex
    safe_tx_hash: str             # 0x-prefixed 32-byte hex
    bundle_hash: str              # 0x-prefixed 32-byte hex
    chain_id: int
    safe_address: str
    safe_nonce: int
    timestamp: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Simulation oracle (KeeperHub)
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    """Patriarch publishes this on SIM_ORACLE_REQUEST; KeeperHub consumes."""
    request_id: str
    proposal_id: str
    iteration: int = 1
    safe_address: str
    to: str                       # Universal Router address
    value: int = 0
    data_hex: str                 # full calldata hex
    operation: int = 0            # 0=CALL, 1=DELEGATECALL
    fork_block: Optional[int] = None
    requested_by: str             # node_id (e.g. "Patriarch_Node_B")
    timestamp: float = Field(default_factory=time.time)


class SimulationResult(BaseModel):
    """KeeperHub publishes this on SIM_ORACLE_RESULT, signed by attestor."""
    request_id: str
    proposal_id: str
    success: bool
    gas_used: int
    return_data: str
    revert_reason: Optional[str] = None
    fork_block: int
    simulator_signature: str       # signature over canonical sim-result digest
    attestor_address: Optional[str] = None
    timestamp: float


# ---------------------------------------------------------------------------
# 0G receipts (audit chain)
# ---------------------------------------------------------------------------

class BaseReceipt(BaseModel):
    """Base shape of every receipt written to 0G via MemoryManager.write_artifact()."""
    schema_version: int = 5
    receipt_type: str
    receipt_id: str
    timestamp: float
    prev_0g_tx_hash: Optional[str] = None
    payload: dict
    receipt_hash: Optional[str] = None  # set by MemoryManager after canonicalization


class LLMContext(BaseModel):
    """Reproducible LLM call context — written to 0G after every LLM invocation."""
    schema_version: int = 1
    call_id: str
    invoking_agent: Literal["Quant_Node_A", "Patriarch_Node_B"]
    invoked_at: float
    proposal_id: str
    iteration: int
    model_id: str
    temperature: float
    seed: Optional[int] = None
    structured_output_schema_hash: str
    structured_output_schema_name: str
    system_prompt: str
    messages: list[dict]
    response_raw: str
    response_parsed_hash: str
    tools_invoked: list[str] = []
    context_hash: str


class AttackRejection(BaseModel):
    """Forensic record published on ATTACK_REJECTED + persisted to 0G."""
    attack_id: str
    attacker_node_id: str = "unknown"
    attack_kind: str
    detected_at: float = Field(default_factory=time.time)
    detected_by: str               # e.g. "Patriarch_Node_B"
    evidence: dict
    rejection_reason: str
    publish_to_0g: bool = True


class MarketSnapshot(BaseModel):
    """Quant publishes the raw market data + its keccak hash so Patriarch can recheck."""
    market_snapshot_hash: str
    market_data: dict
    captured_at: float = Field(default_factory=time.time)
    captured_by: str = "Quant_Node_A"


class Heartbeat(BaseModel):
    """Every long-running daemon publishes this on HEARTBEAT every ~10s."""
    node_id: str
    role: Literal["Quant_Node_A", "Patriarch_Node_B", "Execution_Node_P3",
                  "KeeperHub_Sim_P4", "Adversary_Node_Z"]
    timestamp: float = Field(default_factory=time.time)
    last_seen_proposal: Optional[str] = None
    last_seen_block: Optional[int] = None
    git_sha: Optional[str] = None


class ExecutionReceipt(BaseModel):
    """Published on EXECUTION_SUCCESS + persisted to 0G with hash chain."""
    proposal_id: str
    iteration: int
    safe_address: str
    safe_nonce: int
    tx_hash: str                   # on-chain Sepolia tx hash
    sbt_token_id: Optional[str] = None
    sbt_tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)


class ExecutionFailure(BaseModel):
    """Published on EXECUTION_FAILURE + persisted to 0G."""
    proposal_id: str
    iteration: int
    safe_address: str
    safe_nonce: int
    failure_kind: Literal["REVERT", "GAS_LIMIT", "TIMEOUT", "RPC_ERROR", "OTHER"]
    detail: str
    timestamp: float = Field(default_factory=time.time)


class ProposalEvaluation(BaseModel):
    """LLM-bound output schema for Patriarch's evaluate node."""
    proposal_id: str
    iteration: int
    consensus_status: Literal["ACCEPTED", "REJECTED"]
    rejection_reason: Optional[Literal[
        "RISK_OVERRUN", "MATH_MISMATCH", "OUTSIDE_MANDATE", "GAS_INEFFICIENT",
        "WHITELIST_VIOLATION", "TIMING_RISK", "SIM_REVERT", "OTHER"
    ]] = None
    rejection_detail: Optional[str] = None


# ---------------------------------------------------------------------------
# AXL envelope (per §3.3 — every published payload is wrapped + signed)
# ---------------------------------------------------------------------------

class AXLEnvelope(BaseModel):
    topic: str
    producer_node_id: str
    producer_pubkey: str           # hex pubkey of the producer
    producer_signature: str        # secp256k1 sig over canonical(payload+topic+ts)
    timestamp: float
    payload: dict
