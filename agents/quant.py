import json
import logging
from typing import TypedDict, Annotated, Sequence, Optional
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from core.models import Proposal, ConsensusStatus, ActionType
from core.market_god import generate_market_data
from pydantic import ValidationError
import os
from dotenv import load_dotenv
from memory.memory_manager import MemoryManager

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
    quant_analysis: Optional[dict]
    historical_context: list
    current_proposal: Optional[Proposal]
    patriarch_feedback: Optional[str]
    iteration: int

# --- Nodes ---
def quantitative_ingestion(state: AgentState):
    """Ingests market data and runs deterministic math models."""
    market_data = state.get("market_data", generate_market_data("normal"))
    analysis = calculate_optimal_rotation(market_data)
    
    return {
        "market_data": market_data,
        "quant_analysis": analysis,
        "iteration": state.get("iteration", 0) + 1
    }

def recall_memory(state: AgentState):
    """Queries ChromaDB/0G for historical decisions related to the current analysis."""
    analysis = state.get("quant_analysis")
    if not analysis or analysis["suggested_action"] == "NONE":
        return {"historical_context": []}
        
    mm = MemoryManager()
    query = f"Action: {analysis['suggested_action']}"
    history = mm.query_historical_decisions(query, n_results=2)
    return {"historical_context": history}

def generate_proposal(state: AgentState):
    """Uses LLM to translate math analysis into a structured JSON Proposal."""
    analysis = state.get("quant_analysis")
    feedback = state.get("patriarch_feedback")
    
    if analysis and analysis["suggested_action"] == "NONE" and not feedback:
        logger.info("No actionable trade identified by math models.")
        return {"current_proposal": None}

    llm = ChatOpenAI(model="gpt-5.4-nano", temperature=0.2)
    structured_llm = llm.with_structured_output(Proposal)
    
    system_prompt = f"""
    You are the Yield Quant agent for Arbiter Capital. 
    Your strict objective is to translate the provided quantitative analysis into a valid structured Proposal.
    
    Quantitative Analysis:
    {json.dumps(analysis, indent=2) if analysis else "N/A"}
    
    Historical Context (Past decisions verified on 0G):
    {json.dumps(state.get('historical_context', []), indent=2)}
    
    Rules:
    - Target protocol MUST be Uniswap_V4.
    - If rotating to USDC, suggest a Volatility_Oracle hook.
    - Base all numbers on the provided analysis. Do not invent yields or risk scores.
    - Use historical context to inform your rationale.
    """
    
    if feedback:
        system_prompt += f"\n\nCRITICAL: Your previous proposal was REJECTED by the Risk Patriarch. \nFeedback from Patriarch: {feedback}\nYou MUST adjust your next proposal to address these specific risk concerns while still pursuing yield optimization."

    messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
    
    try:
        proposal = structured_llm.invoke(messages)
        logger.info(f"Drafted Proposal: {proposal.proposal_id} (Iteration: {state.get('iteration')})")
        return {
            "current_proposal": proposal, 
            "messages": [HumanMessage(content=f"Generated proposal: {proposal.json()}") ]
        }
    except Exception as e:
        logger.error(f"Failed to generate valid proposal: {e}")
        return {"current_proposal": None}

# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("ingest_data", quantitative_ingestion)
workflow.add_node("recall_memory", recall_memory)
workflow.add_node("draft_proposal", generate_proposal)

workflow.set_entry_point("ingest_data")
workflow.add_edge("ingest_data", "recall_memory")
workflow.add_edge("recall_memory", "draft_proposal")
workflow.add_edge("draft_proposal", END)

quant_app = workflow.compile()

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("Please set OPENAI_API_KEY in .env")
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
