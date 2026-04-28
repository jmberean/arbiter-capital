from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Literal
from eth_utils import keccak
import json

class ActionType(str, Enum):
    SWAP = "SWAP"
    STAKE = "STAKE"
    PROVIDE_LIQUIDITY = "PROVIDE_LIQUIDITY"
    EMERGENCY_WITHDRAW = "EMERGENCY_WITHDRAW"
    BRIDGE = "BRIDGE"
    STAKE_LST = "STAKE_LST" # e.g. ETH -> stETH
    YIELD_TRADE = "YIELD_TRADE" # e.g. Pendle PT/YT trading

class ConsensusStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

DECIMALS_BY_SYMBOL = {"WETH":18, "stETH":18, "USDC":6, "WBTC":8, "PT-USDC":6, "SOL":9}

class Proposal(BaseModel):
    # Identity
    proposal_id: str = Field(..., description="Unique identifier for the proposal")
    parent_proposal_id: Optional[str] = None
    iteration: int = 1

    # Trade specification
    target_protocol: str = Field(..., description="The target DeFi protocol (e.g., Uniswap_V4)")
    v4_hook_required: Optional[str] = Field(None, description="Specific v4 hook required, if any")
    action: ActionType = Field(..., description="Action to perform")
    asset_in: str = Field(..., description="Asset to trade or use")
    asset_out: Optional[str] = Field(None, description="Expected asset to receive")
    
    asset_in_decimals: Optional[int] = None
    asset_out_decimals: Optional[int] = None
    
    amount_in: Optional[float] = None # Legacy float
    amount_in_units: Optional[str] = None # Base-units string
    min_amount_out_units: Optional[str] = None
    deadline_unix: Optional[int] = None

    # Quantitative attestation
    projected_apy: Optional[float] = None # Legacy
    projected_apy_bps: Optional[int] = None
    risk_score_evaluation: Optional[float] = Field(None, ge=0.0, le=10.0)  # Legacy, 0–10 scale
    risk_score_bps: Optional[int] = None
    quant_analysis_hash: Optional[str] = None

    # Market input snapshot
    market_snapshot_hash: Optional[str] = None

    # LLM provenance
    llm_context_hash: Optional[str] = None
    llm_context_0g_tx: Optional[str] = None

    # Negotiation
    rationale: str = Field(..., description="Detailed explanation")
    consensus_status: ConsensusStatus = Field(default=ConsensusStatus.PENDING)

    # Cryptographic envelope
    proposal_hash: Optional[str] = None
    safe_tx_hash: Optional[str] = None
    quant_signature: Optional[str] = None
    patriarch_signature: Optional[str] = None
    safe_nonce: Optional[int] = None
    chain_id: int = 11155111 # Default Sepolia

    @model_validator(mode="after")
    def _populate(self):
        if self.amount_in_units is None and self.amount_in is not None:
            d = self.asset_in_decimals or DECIMALS_BY_SYMBOL.get(self.asset_in, 18)
            self.amount_in_units = str(int(self.amount_in * (10**d)))
            self.asset_in_decimals = d
        if self.projected_apy_bps is None and self.projected_apy is not None:
            self.projected_apy_bps = int(self.projected_apy * 100)
        if self.risk_score_bps is None and self.risk_score_evaluation is not None:
            self.risk_score_bps = int(self.risk_score_evaluation * 1000)
        return self

class ConsensusMessage(BaseModel):
    proposal_id: str
    iteration: int = 1
    signer_id: str
    signer_address: Optional[str] = None
    role: Optional[str] = "approver"
    signature: str
    safe_tx_hash: str
    timestamp: float

class SimulationResult(BaseModel):
    request_id: str
    proposal_id: str
    success: bool
    gas_used: int
    return_data: str
    revert_reason: Optional[str] = None
    fork_block: int
    simulator_signature: str
    timestamp: float


class LLMContext(BaseModel):
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
