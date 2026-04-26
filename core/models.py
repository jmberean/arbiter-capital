from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict

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

class Proposal(BaseModel):
    proposal_id: str = Field(..., description="Unique identifier for the proposal")
    target_protocol: str = Field(..., description="The target DeFi protocol (e.g., Uniswap_V4)")
    v4_hook_required: Optional[str] = Field(None, description="Specific v4 hook required, if any (e.g., Volatility_Oracle)")
    action: ActionType = Field(..., description="Action to perform (e.g., SWAP)")
    asset_in: str = Field(..., description="Asset to trade or use (e.g., WETH)")
    asset_out: Optional[str] = Field(None, description="Expected asset to receive (e.g., USDC)")
    amount_in: float = Field(..., description="Amount of asset_in to use")
    projected_apy: float = Field(..., description="Projected APY or yield percentage")
    risk_score_evaluation: float = Field(..., ge=0.0, le=10.0, description="Risk score from 0.0 to 10.0")
    rationale: str = Field(..., description="Detailed explanation of the strategy and reasoning")
    consensus_status: ConsensusStatus = Field(default=ConsensusStatus.PENDING, description="Current consensus status of the proposal")
    safe_tx_hash: Optional[str] = Field(None, description="The EIP-712 hash of the Safe transaction for signing")

class ConsensusMessage(BaseModel):
    proposal_id: str = Field(..., description="The proposal being signed")
    signer_id: str = Field(..., description="The ID of the agent signing (e.g. Patriarch)")
    signature: str = Field(..., description="The cryptographic signature (hex)")
    safe_tx_hash: str = Field(..., description="The hash that was signed")
    timestamp: float = Field(..., description="Time of signature")
