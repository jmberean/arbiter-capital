import json
import logging
import uuid
import time
from typing import TypedDict, Annotated, Sequence, Optional, Literal
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from core.models import Proposal, ConsensusStatus, ActionType, LLMContext
from core.market_god import generate_market_data
from core.crypto import proposal_eip712_digest, bundle_hash, sign_digest
from core.identity import QUANT_KEY, QUANT_ADDR
from core.persistence import CursorStore
from eth_utils import keccak
import os
from dotenv import load_dotenv
from memory.memory_manager import MemoryManager
from memory.llm_context_writer import capture_and_persist
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantAgent")

# --- Math-First Tooling ---
def calculate_optimal_rotation(market_data: dict) -> dict:
    """
    Deterministic Python tool that performs actual math on market data.
    """
    logger.info("Executing mathematical forecasting...")
    assets = market_data["assets"]
    network = market_data.get("network", {"gas_price_gwei": 25.0})
    
    eth_vol = assets["WETH"]["volatility_48h"]
    steth_yield = assets.get("stETH", {}).get("staking_yield", 0.0)
    pendle_yield = assets.get("PENDLE_PT_USDC", {}).get("implied_yield", 0.0)
    sol_safety = assets["SOL"].get("safety_score", 10.0)
    
    gas_cost_usd = ((network["gas_price_gwei"] * 1e-9) * 150000) * assets["WETH"]["price"]
    
    recommendation = {
        "analysis": f"Gas Cost: ${round(gas_cost_usd, 2)}, Pendle Yield: {pendle_yield*100}%, LST Yield: {steth_yield*100}%",
        "suggested_action": "NONE",
        "target_protocol": "Uniswap_V4",
        "projected_apy": 0.0,
        "risk_score": 1.0
    }

    if sol_safety < 4.0:
        recommendation["suggested_action"] = "EMERGENCY_WITHDRAW"
        recommendation["rationale"] = f"CRITICAL: Protocol safety score cratered."
        recommendation["risk_score"] = 9.5
        return recommendation

    if pendle_yield > 0.15:
        if (10000 * (pendle_yield - 0.04) / 52) > gas_cost_usd:
            recommendation["suggested_action"] = "YIELD_TRADE"
            recommendation["target_protocol"] = "Pendle"
            recommendation["rationale"] = f"Massive yield spread on Pendle PT-USDC."
            recommendation["projected_apy"] = pendle_yield
            recommendation["risk_score"] = 5.5
            return recommendation

    if steth_yield > (assets["WETH"]["staking_yield"] + 0.02):
        recommendation["suggested_action"] = "STAKE_LST"
        recommendation["target_protocol"] = "Lido"
        recommendation["rationale"] = f"LST yield spread > 2%."
        recommendation["projected_apy"] = steth_yield
        recommendation["risk_score"] = 3.0
        return recommendation
        
    if eth_vol > 0.15:
        recommendation["suggested_action"] = "SWAP"
        recommendation["asset_out"] = "USDC"
        recommendation["rationale"] = "High volatility on ETH. Rotate to stablecoin."
        recommendation["projected_apy"] = 0.04
        recommendation["risk_score"] = 2.0
    
    return recommendation

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    market_data: dict
    quant_analysis: Optional[dict]
    quant_analysis_hash: Optional[str]
    market_snapshot_hash: Optional[str]
    historical_context: list
    current_proposal: Optional[Proposal]
    patriarch_feedback: Optional[str]
    iteration: int
    llm_raw_response: Optional[str]
    llm_messages: Optional[list]

# --- Nodes ---
def quantitative_ingestion(state: AgentState):
    """Ingests market data and runs deterministic math models."""
    market_data = state.get("market_data", generate_market_data("normal"))
    analysis = calculate_optimal_rotation(market_data)
    
    canonical = json.dumps(analysis, sort_keys=True, separators=(",",":")).encode()
    snapshot_canonical = json.dumps(market_data, sort_keys=True, separators=(",",":")).encode()
    
    return {
        "market_data": market_data,
        "quant_analysis": analysis,
        "quant_analysis_hash": "0x" + keccak(canonical).hex(),
        "market_snapshot_hash": "0x" + keccak(snapshot_canonical).hex(),
        "iteration": state.get("iteration", 0) + 1
    }

def recall_memory(state: AgentState):
    analysis = state.get("quant_analysis")
    if not analysis or analysis["suggested_action"] == "NONE":
        return {"historical_context": []}
    mm = MemoryManager()
    query = f"Action: {analysis['suggested_action']}"
    history = mm.query_historical_decisions(query, n_results=2)
    return {"historical_context": history}

def generate_proposal(state: AgentState):
    analysis = state.get("quant_analysis")
    feedback = state.get("patriarch_feedback")
    if analysis and analysis["suggested_action"] == "NONE" and not feedback:
        return {"current_proposal": None}

    model_id = "gpt-4o"
    temperature = 0.2
    llm = ChatOpenAI(model=model_id, temperature=temperature)
    structured_llm = llm.with_structured_output(Proposal)
    
    system_prompt = f"""
    You are the Yield Quant agent for Arbiter Capital.
    Quantitative Analysis: {json.dumps(analysis)}
    """
    messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
    
    try:
        proposal = structured_llm.invoke(messages)
        # We'd ideally get the raw response here. For mock, we'll simulate.
        return {
            "current_proposal": proposal,
            "llm_raw_response": proposal.model_dump_json(),
            "llm_messages": [m.dict() for m in messages]
        }
    except Exception as e:
        logger.error(f"Failed to generate proposal: {e}")
        return {"current_proposal": None}

def capture_llm_context_node(state: AgentState):
    p = state["current_proposal"]
    if p is None: return {}
    
    ctx_hash, tx_hash = capture_and_persist(
        agent="Quant_Node_A",
        proposal_id=p.proposal_id,
        iteration=p.iteration,
        model_id="gpt-4o",
        temperature=0.2,
        seed=None,
        schema=Proposal.model_json_schema(),
        schema_name="Proposal",
        system_prompt="...", # simplified
        messages=state["llm_messages"],
        response_raw=state["llm_raw_response"],
        parsed_obj=p,
        tools_invoked=[]
    )
    p.llm_context_hash = ctx_hash
    p.llm_context_0g_tx = tx_hash
    return {"current_proposal": p}

def self_audit(state: AgentState):
    p, a = state["current_proposal"], state["quant_analysis"]
    if p is None: return {}
    # Basic math invariant check
    if p.quant_analysis_hash != state["quant_analysis_hash"]:
        logger.warning("Self-audit failed: analysis hash mismatch.")
        return {"current_proposal": None}
    return {}

def sign_proposal(state: AgentState):
    p: Proposal = state["current_proposal"]
    if p is None: return {}
    
    treasury = SafeTreasury()
    router = UniswapV4Router()
    calldata = router.generate_calldata(p)
    
    # In live mode this would call treasury.read_nonce()
    p.safe_nonce = 0 
    p.quant_analysis_hash = state["quant_analysis_hash"]
    p.market_snapshot_hash = state["market_snapshot_hash"]
    
    p.safe_tx_hash = treasury.get_safe_tx_hash(os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x000000000022D473030F116dDEE9F6B43aC78BA3"), calldata)
    
    p_digest = proposal_eip712_digest(p.model_dump(by_alias=True), os.getenv("SAFE_ADDRESS", "0x0000000000000000000000000000000000000000"), p.chain_id)
    p.proposal_hash = "0x" + p_digest.hex()
    
    b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
    
    if QUANT_KEY:
        sig_bundle = sign_digest(b_digest, QUANT_KEY)
        sig_safe   = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), QUANT_KEY)
        p.quant_signature = sig_bundle + sig_safe[2:]
        logger.info(f"Signed proposal {p.proposal_id}")
        
    return {"current_proposal": p}

# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("ingest_data", quantitative_ingestion)
workflow.add_node("recall_memory", recall_memory)
workflow.add_node("draft_proposal", generate_proposal)
workflow.add_node("capture_llm_context", capture_llm_context_node)
workflow.add_node("self_audit", self_audit)
workflow.add_node("sign_proposal", sign_proposal)

workflow.set_entry_point("ingest_data")
workflow.add_edge("ingest_data", "recall_memory")
workflow.add_edge("recall_memory", "draft_proposal")
workflow.add_edge("draft_proposal", "capture_llm_context")
workflow.add_edge("capture_llm_context", "self_audit")
workflow.add_edge("self_audit", "sign_proposal")
workflow.add_edge("sign_proposal", END)

quant_app = workflow.compile()
