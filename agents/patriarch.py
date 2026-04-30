import json
import logging
import os
import time
import operator
import uuid
from typing import TypedDict, Annotated, Sequence, Optional

from dotenv import load_dotenv
from eth_utils import keccak
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from agents.quant import calculate_optimal_rotation
from core.crypto import sim_result_digest, recover_signer
from core.identity import is_attestor
from core.models import (
    Proposal, ConsensusStatus, ActionType,
    ProposalEvaluation, SimulationResult,
)
from memory.llm_context_writer import capture_and_persist

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatriarchAgent")

LLM_SEED = int(os.getenv("LLM_SEED", "42"))

PATRIARCH_SYSTEM_PROMPT = (
    "You are the Risk Patriarch agent for Arbiter Capital. "
    "Your sole objective is capital preservation. "
    "Evaluate the incoming Proposal against institutional risk policy. "
    "Output ONLY a ProposalEvaluation. If REJECTED, choose the most specific "
    "rejection_reason from the enum and write a one-line rejection_detail."
)


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
    llm_system_prompt: Optional[str]
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
    canonical = json.dumps(a, sort_keys=True, separators=(",", ":")).encode()
    expected = "0x" + keccak(canonical).hex()

    if expected != p.quant_analysis_hash:
        logger.warning(f"Math mismatch: expected {expected}, got {p.quant_analysis_hash}")
        return {"reviewed_proposal": _reject(
            p, "MATH_MISMATCH",
            f"recomputed {expected[:18]}…, claimed {(p.quant_analysis_hash or '0x')[:18]}…"
        )}

    return {"patriarch_recompute": a}


def evaluate_proposal(state: AgentState):
    p = state["incoming_proposal"]
    if state.get("reviewed_proposal"):
        return {}  # already rejected in recheck

    model_id = "gpt-4o"
    temperature = 0.0
    llm = ChatOpenAI(model=model_id, temperature=temperature, seed=LLM_SEED)
    structured_llm = llm.with_structured_output(ProposalEvaluation)

    messages = [
        SystemMessage(content=PATRIARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Evaluate this proposal:\n{p.model_dump_json(indent=2)}"),
    ]

    try:
        ev = structured_llm.invoke(messages)

        ctx_hash, tx_hash = capture_and_persist(
            agent="Patriarch_Node_B",
            proposal_id=p.proposal_id,
            iteration=p.iteration,
            model_id=model_id,
            temperature=temperature,
            seed=LLM_SEED,
            schema=ProposalEvaluation.model_json_schema(),
            schema_name="ProposalEvaluation",
            system_prompt=PATRIARCH_SYSTEM_PROMPT,
            messages=[m.dict() for m in messages],
            response_raw=ev.model_dump_json(),
            parsed_obj=ev,
            tools_invoked=[],
        )

        reviewed = p.model_copy(deep=True)
        reviewed.consensus_status = ConsensusStatus(ev.consensus_status)
        if ev.consensus_status == "REJECTED":
            reviewed.rationale += f" | REJECTED: {ev.rejection_reason} - {ev.rejection_detail}"

        return {
            "evaluation_pre_sim": ev,
            "reviewed_proposal": reviewed,
            "llm_raw_response": ev.model_dump_json(),
            "llm_messages": [m.dict() for m in messages],
            "llm_system_prompt": PATRIARCH_SYSTEM_PROMPT,
        }
    except Exception as e:
        logger.error(f"Failed to evaluate proposal: {e}")
        return {"reviewed_proposal": _reject(p, "OTHER", str(e))}


def consult_sim_oracle(state: AgentState):
    """Consult the KeeperHub Sim Oracle and verify the attestor signature.

    Per spec §6.3 + §12:
      - Skip if already rejected.
      - Verify simulator_signature recovers to a registered ATTESTOR.
      - On REVERT: override to REJECTED(SIM_REVERT).
      - On TIMEOUT or unsigned/invalid attestor: override to REJECTED(OUTSIDE_MANDATE).
    """
    pre_sim = state.get("evaluation_pre_sim")
    if pre_sim is None or pre_sim.consensus_status != "ACCEPTED":
        return {}

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

        # ── Attestor signature verification (§12) ───────────────────────────
        sim_sig = sim_data.get("simulator_signature", "")
        if not sim_sig or sim_sig == "0x" + "00" * 65:
            logger.warning(f"Sim oracle returned no/zero signature for {p.proposal_id}; treating as untrusted.")
            reviewed = state["reviewed_proposal"].model_copy(deep=True)
            reviewed.consensus_status = ConsensusStatus.REJECTED
            reviewed.rationale += " | OUTSIDE_MANDATE: sim oracle unsigned"
            return {"reviewed_proposal": reviewed, "sim_result": sim_data}

        digest = sim_result_digest(
            proposal_id=p.proposal_id,
            iteration=p.iteration,
            success=sim_data.get("success", False),
            gas_used=sim_data.get("gas_used", 0),
            return_data=sim_data.get("return_data", "0x"),
            fork_block=sim_data.get("fork_block", 0),
        )
        try:
            recovered = recover_signer(digest, sim_sig)
        except Exception as sig_err:
            logger.warning(f"Sim sig invalid for {p.proposal_id}: {sig_err}")
            reviewed = state["reviewed_proposal"].model_copy(deep=True)
            reviewed.consensus_status = ConsensusStatus.REJECTED
            reviewed.rationale += f" | OUTSIDE_MANDATE: sim sig invalid ({sig_err})"
            return {"reviewed_proposal": reviewed, "sim_result": sim_data}

        if not is_attestor(recovered):
            logger.warning(f"Sim sig from non-attestor {recovered} for {p.proposal_id}")
            reviewed = state["reviewed_proposal"].model_copy(deep=True)
            reviewed.consensus_status = ConsensusStatus.REJECTED
            reviewed.rationale += f" | OUTSIDE_MANDATE: sim attestor unrecognized ({recovered})"
            return {"reviewed_proposal": reviewed, "sim_result": sim_data}

        logger.info(
            f"Sim oracle: success={sim_data.get('success')} attestor={recovered} for {p.proposal_id}"
        )

        # ── Honor REVERT verdict ─────────────────────────────────────────────
        if not sim_data.get("success", True):
            reviewed = state["reviewed_proposal"].model_copy(deep=True)
            reviewed.consensus_status = ConsensusStatus.REJECTED
            reviewed.rationale += f" | SIM_REVERT: {sim_data.get('revert_reason', 'unknown')}"
            return {"reviewed_proposal": reviewed, "sim_result": sim_data}

        return {"sim_result": sim_data}

    except Exception as e:
        # Per §6.3: treat sim oracle failure as auto-reject OUTSIDE_MANDATE
        logger.warning(f"Sim oracle unavailable ({e}) — rejecting OUTSIDE_MANDATE")
        reviewed = state["reviewed_proposal"].model_copy(deep=True)
        reviewed.consensus_status = ConsensusStatus.REJECTED
        reviewed.rationale += f" | OUTSIDE_MANDATE: sim oracle timeout ({e})"
        return {"reviewed_proposal": reviewed}


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
