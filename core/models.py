from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class ActionType(str, Enum):
    SWAP = "SWAP"
    STAKE = "STAKE"
    PROVIDE_LIQUIDITY = "PROVIDE_LIQUIDITY"

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
