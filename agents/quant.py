import json
import logging
from typing import TypedDict, Annotated, Sequence, Optional
import operator
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from core.models import Proposal, ConsensusStatus, ActionType
from core.market_god import generate_market_data
from pydantic import ValidationError
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantAgent")

# --- Math-First Tooling ---
def calculate_optimal_rotation(market_data: dict) -> dict:
    """
    Deterministic Python tool that performs actual math on market data,
    rather than letting the LLM guess numbers.
    """
    logger.info("Executing mathematical forecasting...")
    assets = market_data["assets"]
    
    # Simple strategy: If ETH volatility is high, rotate to USDC or higher yield SOL
    eth_vol = assets["WETH"]["volatility_48h"]
    sol_yield = assets["SOL"]["staking_yield"]
    
    recommendation = {
        "analysis": f"ETH 48h Volatility is {eth_vol*100}%. SOL Yield is {sol_yield*100}%.",
        "suggested_action": "NONE",
        "target_protocol": "Uniswap_V4"
    }

    if eth_vol > 0.15: # High volatility
        recommendation["suggested_action"] = "SWAP_WETH_TO_USDC"
        recommendation["rationale"] = "High volatility detected. Rotate to stablecoin to preserve capital."
        recommendation["projected_apy"] = assets["USDC"]["staking_yield"] * 100
        recommendation["risk_score"] = 2.0
    elif sol_yield > 0.08: # High yield opportunity
        recommendation["suggested_action"] = "SWAP_WETH_TO_SOL"
        recommendation["rationale"] = "Significant yield spread detected on SOL. Reallocate capital for yield maximization."
        recommendation["projected_apy"] = sol_yield * 100
        recommendation["risk_score"] = 6.5
    else:
         recommendation["rationale"] = "Market conditions stable. No immediate action required."

    return recommendation

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    market_data: dict
    quant_analysis: dict
    current_proposal: Optional[Proposal]
    iteration: int

# --- Nodes ---
def quantitative_ingestion(state: AgentState):
    """Ingests market data and runs deterministic math models."""
    market_data = state.get("market_data", generate_market_data("normal"))
    analysis = calculate_optimal_rotation(market_data)
    
    # Pass the data along to the LLM context
    return {
        "market_data": market_data,
        "quant_analysis": analysis,
        "iteration": state.get("iteration", 0) + 1
    }

def generate_proposal(state: AgentState):
    """Uses LLM to translate math analysis into a structured JSON Proposal."""
    analysis = state["quant_analysis"]
    
    if analysis["suggested_action"] == "NONE":
        logger.info("No actionable trade identified by math models.")
        return {"current_proposal": None}

    llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.2)
    # We instruct the LLM to strictly output the JSON structure matching our Pydantic model
    structured_llm = llm.with_structured_output(Proposal)
    
    system_prompt = f"""
    You are the Yield Quant agent for Arbiter Capital. 
    Your strict objective is to translate the provided quantitative analysis into a valid structured Proposal.
    
    Quantitative Analysis:
    {json.dumps(analysis, indent=2)}
    
    Rules:
    - Target protocol MUST be Uniswap_V4.
    - If rotating to USDC, suggest a Volatility_Oracle hook.
    - Base all numbers on the provided analysis. Do not invent yields or risk scores.
    """
    
    # If there are previous messages (e.g., feedback from Patriarch), include them
    messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
    
    try:
        proposal = structured_llm.invoke(messages)
        logger.info(f"Drafted Proposal: {proposal.proposal_id}")
        return {"current_proposal": proposal, "messages": [HumanMessage(content=f"Generated proposal: {proposal.json()}") ]}
    except Exception as e:
        logger.error(f"Failed to generate valid proposal: {e}")
        return {"current_proposal": None}

# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("ingest_data", quantitative_ingestion)
workflow.add_node("draft_proposal", generate_proposal)

workflow.set_entry_point("ingest_data")
workflow.add_edge("ingest_data", "draft_proposal")
workflow.add_edge("draft_proposal", END)

quant_app = workflow.compile()

if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("Please set ANTHROPIC_API_KEY in .env")
        exit(1)
        
    print("Testing Quant Agent with Flash Crash data...")
    state = {
        "market_data": generate_market_data("flash_crash_eth"),
        "messages": [],
        "iteration": 0
    }
    result = quant_app.invoke(state)
    if result.get("current_proposal"):
        print("\nFinal Output JSON:")
        print(result["current_proposal"].model_dump_json(indent=2))
