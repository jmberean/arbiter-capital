import json
import logging
import os
import time
import operator
from typing import TypedDict, Annotated, Sequence, Optional, Literal

from dotenv import load_dotenv
from eth_utils import keccak
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, ValidationError

from agents.quant import calculate_optimal_rotation
from core.models import Proposal, ConsensusStatus, ActionType
from memory.llm_context_writer import capture_and_persist

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchAgent")

class ProposalEvaluation(BaseModel):
    proposal_id: str
    iteration: int
    consensus_status: Literal["ACCEPTED","REJECTED"]
    rejection_reason: Optional[Literal[
        "RISK_OVERRUN","MATH_MISMATCH","OUTSIDE_MANDATE","GAS_INEFFICIENT",
        "WHITELIST_VIOLATION","TIMING_RISK","SIM_REVERT","OTHER"]] = None
    rejection_detail: Optional[str] = None

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    incoming_proposal: Optional[Proposal]
    market_data: Optional[dict]
    patriarch_recompute: Optional[dict]
    evaluation_pre_sim: Optional[ProposalEvaluation]
    reviewed_proposal: Optional[Proposal]
    llm_raw_response: Optional[str]
    llm_messages: Optional[list]
    sim_result: Optional[dict]

def _reject(p: Proposal, reason: str, detail: str) -> Proposal:
    reviewed = p.model_copy(deep=True)
    reviewed.consensus_status = ConsensusStatus.REJECTED
    reviewed.rationale += f" | REJECTED: {reason} - {detail}"
    return reviewed

# --- Nodes ---
def deterministic_recheck(state: AgentState):
    p = state["incoming_proposal"]
    md = state.get("market_data")
    if not md:
        return {"reviewed_proposal": _reject(p, "MATH_MISMATCH", "no market_data provided")}
    
    a = calculate_optimal_rotation(md)
    canonical = json.dumps(a, sort_keys=True, separators=(",",":")).encode()
    expected = "0x" + keccak(canonical).hex()
    
    if expected != p.quant_analysis_hash:
        logger.warning(f"Math mismatch: expected {expected}, got {p.quant_analysis_hash}")
        return {"reviewed_proposal": _reject(p, "MATH_MISMATCH", f"recomputed {expected}, claimed {p.quant_analysis_hash}")}
    
    return {"patriarch_recompute": a}

def evaluate_proposal(state: AgentState):
    p = state["incoming_proposal"]
    if state.get("reviewed_proposal"): return {} # already rejected in recheck

    model_id = "gpt-4o"
    temperature = 0.1
    llm = ChatOpenAI(model=model_id, temperature=temperature)
    structured_llm = llm.with_structured_output(ProposalEvaluation)
    
    system_prompt = """
    You are the Risk Patriarch agent for Arbiter Capital.
    Your objective is capital preservation. Evaluate the incoming Proposal.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Evaluate this proposal:\n{p.model_dump_json(indent=2)}")
    ]
    
    try:
        ev = structured_llm.invoke(messages)
        
        # Capture LLM context
        ctx_hash, tx_hash = capture_and_persist(
            agent="Patriarch_Node_B",
            proposal_id=p.proposal_id,
            iteration=p.iteration,
            model_id=model_id,
            temperature=temperature,
            seed=None,
            schema=ProposalEvaluation.model_json_schema(),
            schema_name="ProposalEvaluation",
            system_prompt=system_prompt,
            messages=[m.dict() for m in messages],
            response_raw=ev.model_dump_json(),
            parsed_obj=ev,
            tools_invoked=[]
        )
        
        reviewed = p.model_copy(deep=True)
        reviewed.consensus_status = ConsensusStatus(ev.consensus_status)
        if ev.consensus_status == "REJECTED":
            reviewed.rationale += f" | REJECTED: {ev.rejection_reason} - {ev.rejection_detail}"
        
        return {
            "evaluation_pre_sim": ev,
            "reviewed_proposal": reviewed,
            "llm_raw_response": ev.model_dump_json(),
            "llm_messages": [m.dict() for m in messages]
        }
    except Exception as e:
        logger.error(f"Failed to evaluate proposal: {e}")
        return {"reviewed_proposal": _reject(p, "OTHER", str(e))}

def consult_sim_oracle(state: AgentState):
    """Call KeeperHub simulation oracle via the LangChain bridge.

    Skipped if the proposal was already rejected by the evaluate node.
    On SIM_REVERT, overrides the reviewed_proposal to REJECTED.
    On failure / timeout, logs a warning and passes through without overriding.
    """
    pre_sim = state.get("evaluation_pre_sim")
    if pre_sim is None or pre_sim.consensus_status != "ACCEPTED":
        return {}  # already rejected; no simulation needed

    p = state["incoming_proposal"]
    try:
        from langchain_keeperhub import KeeperHubSimulateTool
        from execution.uniswap_v4.router import UniswapV4Router

        router = UniswapV4Router()
        calldata = router.generate_calldata(p)

        sim_tool = KeeperHubSimulateTool()
        raw = sim_tool.invoke({
            "to": os.getenv("UNIVERSAL_ROUTER_ADDRESS", "0x" + "0" * 40),
            "value": 0,
            "data_hex": "0x" + calldata.hex(),
            "operation": 0,
        })
        sim_data = json.loads(raw) if isinstance(raw, str) else raw
        logger.info(f"Sim oracle result for {p.proposal_id}: success={sim_data.get('success')}")

        if not sim_data.get("success", True):
            reviewed = state["reviewed_proposal"].model_copy(deep=True)
            reviewed.consensus_status = ConsensusStatus.REJECTED
            reviewed.rationale += f" | SIM_REVERT: {sim_data.get('revert_reason', 'unknown')}"
            return {"reviewed_proposal": reviewed, "sim_result": sim_data}

        return {"sim_result": sim_data}

    except Exception as e:
        logger.warning(f"Sim oracle unavailable ({e}) — keeping evaluate result")
        return {}


# --- Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("recheck", deterministic_recheck)
workflow.add_node("evaluate", evaluate_proposal)
workflow.add_node("consult_sim_oracle", consult_sim_oracle)

workflow.set_entry_point("recheck")
workflow.add_edge("recheck", "evaluate")
workflow.add_edge("evaluate", "consult_sim_oracle")
workflow.add_edge("consult_sim_oracle", END)

patriarch_app = workflow.compile()
