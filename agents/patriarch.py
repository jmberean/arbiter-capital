import json
import logging
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from core.models import Proposal, ConsensusStatus
from pydantic import ValidationError
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchAgent")

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    incoming_proposal: Proposal | None
    reviewed_proposal: Proposal | None

# --- Nodes ---
def evaluate_proposal(state: AgentState):
    """Evaluates the incoming proposal against strict risk metrics."""
    proposal = state["incoming_proposal"]
    if not proposal:
        return {"reviewed_proposal": None}

    logger.info(f"Evaluating Proposal ID: {proposal.proposal_id}")

    llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.1)
    
    system_prompt = """
    You are the Risk Patriarch agent for Arbiter Capital.
    Your objective is capital preservation. You must evaluate the incoming Proposal.
    
    Risk Parameters:
    - Maximum acceptable risk_score is 5.0. If higher, REJECT.
    - Target protocol must be Uniswap_V4. If not, REJECT.
    - If the action is SWAP and asset_out is a stablecoin (USDC) during high volatility, favor ACCEPT.
    
    Output JSON format only, matching the exact schema of the incoming proposal, but update the 'consensus_status' to ACCEPTED or REJECTED.
    If REJECTED, append your reasoning to the 'rationale' field.
    """
    
    structured_llm = llm.with_structured_output(Proposal)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Evaluate this proposal:\n{proposal.model_dump_json(indent=2)}")
    ]
    
    try:
        reviewed = structured_llm.invoke(messages)
        
        # Fallback deterministic check in case LLM hallucinations bypass instructions
        if reviewed.risk_score_evaluation > 5.0 and reviewed.consensus_status == ConsensusStatus.ACCEPTED:
             logger.warning("LLM approved a high-risk proposal. Overriding to REJECTED.")
             reviewed.consensus_status = ConsensusStatus.REJECTED
             reviewed.rationale += " | OVERRIDE: Risk score exceeds threshold of 5.0."
             
        logger.info(f"Proposal {reviewed.proposal_id} evaluated as: {reviewed.consensus_status.value}")
        return {"reviewed_proposal": reviewed, "messages": [HumanMessage(content=f"Evaluation complete. Status: {reviewed.consensus_status.value}")]}
        
    except Exception as e:
        logger.error(f"Failed to evaluate proposal: {e}")
        # Default to safe state on error
        proposal.consensus_status = ConsensusStatus.REJECTED
        proposal.rationale += f" | System error during evaluation: {e}"
        return {"reviewed_proposal": proposal}

# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("evaluate", evaluate_proposal)

workflow.set_entry_point("evaluate")
workflow.add_edge("evaluate", END)

patriarch_app = workflow.compile()

if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("Please set ANTHROPIC_API_KEY in .env")
        exit(1)
        
    print("Testing Patriarch Agent...")
    
    # Mock a high-risk proposal from Quant
    mock_proposal = Proposal(
        proposal_id="test_001",
        target_protocol="Uniswap_V4",
        action="SWAP",
        asset_in="WETH",
        asset_out="SOL",
        amount_in=10.0,
        projected_apy=12.0,
        risk_score_evaluation=6.5, # Should trigger rejection
        rationale="High yield rotation.",
        consensus_status=ConsensusStatus.PENDING
    )
    
    state = {
        "incoming_proposal": mock_proposal,
        "messages": []
    }
    
    result = patriarch_app.invoke(state)
    if result.get("reviewed_proposal"):
         print("\nFinal Evaluated JSON:")
         print(result["reviewed_proposal"].model_dump_json(indent=2))
