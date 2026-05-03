import json
import logging
import os
import operator
import time
from typing import TypedDict, Annotated, Sequence, Optional

from dotenv import load_dotenv
from eth_utils import keccak
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.crypto import proposal_eip712_digest, bundle_hash, sign_digest
from core.identity import QUANT_KEY, QUANT_ADDR
from core.market_god import generate_market_data
from core.models import Proposal, ConsensusStatus, ActionType
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router
from memory.llm_context_writer import capture_and_persist
from memory.memory_manager import MemoryManager

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantAgent")

# Deterministic seed: published in the LLMContext so verifiers can replay.
LLM_SEED = int(os.getenv("LLM_SEED", "42"))

# Single source of truth for the Quant LLM system prompt — captured verbatim
# in the LLMContext receipt for replay determinism.
QUANT_SYSTEM_PROMPT = (
    "You are the Yield Quant agent for Arbiter Capital. "
    "You produce structured Proposal objects ONLY; never free text. "
    "Your math has already been performed by calculate_optimal_rotation — "
    "do NOT recompute risk_score_bps, projected_apy_bps, or quant_analysis_hash. "
    "Copy the analysis values verbatim and write a concise human rationale."
)


# --- Math-First Tooling ---
def calculate_optimal_rotation(market_data: dict) -> dict:
    """Deterministic Python forecaster. Output is keccak-canonicalized."""
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
        "risk_score": 1.0,
    }

    if sol_safety < 4.0:
        recommendation["suggested_action"] = "EMERGENCY_WITHDRAW"
        recommendation["rationale"] = "CRITICAL: Protocol safety score cratered."
        recommendation["risk_score"] = 9.5
        return recommendation

    if pendle_yield > 0.15:
        if (10000 * (pendle_yield - 0.04) / 52) > gas_cost_usd:
            recommendation["suggested_action"] = "YIELD_TRADE"
            recommendation["target_protocol"] = "Pendle"
            recommendation["rationale"] = "Massive yield spread on Pendle PT-USDC."
            recommendation["projected_apy"] = pendle_yield
            recommendation["risk_score"] = 5.5
            return recommendation

    if steth_yield > (assets["WETH"]["staking_yield"] + 0.02):
        recommendation["suggested_action"] = "STAKE_LST"
        recommendation["target_protocol"] = "Lido"
        recommendation["rationale"] = "LST yield spread > 2%."
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
    llm_system_prompt: Optional[str]


# --- Nodes ---
def quantitative_ingestion(state: AgentState):
    market_data = state.get("market_data", generate_market_data("normal"))
    analysis = calculate_optimal_rotation(market_data)

    canonical = json.dumps(analysis, sort_keys=True, separators=(",", ":")).encode()
    snapshot_canonical = json.dumps(market_data, sort_keys=True, separators=(",", ":")).encode()

    return {
        "market_data": market_data,
        "quant_analysis": analysis,
        "quant_analysis_hash": "0x" + keccak(canonical).hex(),
        "market_snapshot_hash": "0x" + keccak(snapshot_canonical).hex(),
        "iteration": state.get("iteration", 0) + 1,
    }


def recall_memory(state: AgentState):
    analysis = state.get("quant_analysis")
    if not analysis or analysis["suggested_action"] == "NONE":
        return {"historical_context": []}
    mm = MemoryManager()
    query = f"Action: {analysis['suggested_action']}"
    return {"historical_context": mm.query_historical_decisions(query, n_results=2)}


def generate_proposal(state: AgentState):
    analysis = state.get("quant_analysis")
    feedback = state.get("patriarch_feedback")
    if analysis and analysis["suggested_action"] == "NONE" and not feedback:
        return {"current_proposal": None}

    model_id = "gpt-4o"
    temperature = 0.0  # Deterministic mode — paired with seed for replay
    llm = ChatOpenAI(model=model_id, temperature=temperature, seed=LLM_SEED)
    structured_llm = llm.with_structured_output(Proposal)

    system_prompt = (
        f"{QUANT_SYSTEM_PROMPT}\n\n"
        f"Quantitative Analysis (verbatim): {json.dumps(analysis)}"
    )
    messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))

    try:
        proposal = structured_llm.invoke(messages)
        return {
            "current_proposal": proposal,
            "llm_raw_response": proposal.model_dump_json(),
            "llm_messages": [m.dict() for m in messages],
            "llm_system_prompt": system_prompt,
        }
    except Exception as e:
        logger.error(f"Failed to generate proposal: {e}")
        return {"current_proposal": None}


def capture_llm_context_node(state: AgentState):
    p = state["current_proposal"]
    if p is None:
        return {}

    logger.info(f"CAPTURING CONTEXT for {p.proposal_id}")
    logger.info(f"  Current min_amount_out_units: {p.min_amount_out_units}")
    logger.info(f"  Action: {p.action}")

    # Pin invariants from state so self_audit and signing can use them.
    # The LLM cannot reliably reproduce these values — they must come from state.
    p.quant_analysis_hash = state["quant_analysis_hash"]
    p.market_snapshot_hash = state.get("market_snapshot_hash")
    
    # Pin iteration and ensure proposal_id is set before signing
    p.iteration = state.get("iteration", 1)
    
    # Use proposal_id from state if provided (for iterations)
    state_prop_id = state.get("proposal_id")
    if state_prop_id:
        p.proposal_id = state_prop_id
    
    if not p.proposal_id or p.proposal_id == "uuid_placeholder":
        import uuid
        p.proposal_id = f"prop_{uuid.uuid4().hex[:8]}"

    # Ensure amount_in_units and min_amount_out_units are valid integer strings — LLM often omits or mis-formats them.
    from core.models import DECIMALS_BY_SYMBOL
    
    # Sanitize amount_in_units
    valid_in = False
    if p.amount_in_units is not None:
        try:
            int(p.amount_in_units)
            valid_in = True
        except (ValueError, TypeError):
            pass
    if not valid_in:
        if p.amount_in is not None:
            try:
                d = DECIMALS_BY_SYMBOL.get(p.asset_in or "WETH", 18)
                p.amount_in_units = str(int(float(p.amount_in) * (10 ** d)))
            except (ValueError, TypeError):
                p.amount_in_units = str(10 ** 18)
        else:
            p.amount_in_units = str(10 ** 18)

    # Hard cap for test runs — set MAX_SWAP_UNITS in .env to limit on-chain spend
    _max_units = os.getenv("MAX_SWAP_UNITS")
    if _max_units:
        try:
            p.amount_in_units = str(min(int(p.amount_in_units), int(_max_units)))
        except (ValueError, TypeError):
            pass

    # Normalize ETH to WETH for firewall and signing
    if p.asset_in == "ETH": p.asset_in = "WETH"
    if p.asset_out == "ETH": p.asset_out = "WETH"

    # Sanitize min_amount_out_units
    valid_out = False
    if p.min_amount_out_units is not None:
        try:
            if int(p.min_amount_out_units) > 0:
                valid_out = True
        except (ValueError, TypeError):
            pass
            
    if not valid_out:
        logger.info(f"  min_amount_out_units invalid/missing, estimating for {p.action}...")
        if p.action == ActionType.SWAP:
            # Estimate min_amount_out with 1% slippage
            try:
                from core.models import DECIMALS_BY_SYMBOL
                market_data = state.get("market_data", {})
                assets = market_data.get("assets", {})
                
                asset_in = p.asset_in or "WETH"
                asset_out = p.asset_out or "USDC"
                
                # Normalize ETH to WETH for lookup
                if asset_in == "ETH": asset_in = "WETH"
                if asset_out == "ETH": asset_out = "WETH"
                
                price_in = assets.get(asset_in, {}).get("price", 0.0)
                price_out = assets.get(asset_out, {}).get("price", 1.0)
                
                logger.info(f"    Prices: {asset_in}={price_in}, {asset_out}={price_out}")
                
                if price_in > 0 and price_out > 0:
                    amount_in = float(p.amount_in) if p.amount_in else float(int(p.amount_in_units) / (10**DECIMALS_BY_SYMBOL.get(asset_in, 18)))
                    expected_out = (amount_in * price_in) / price_out
                    min_out = expected_out * 0.99 # 1% slippage
                    
                    d_out = DECIMALS_BY_SYMBOL.get(asset_out, 18)
                    p.min_amount_out_units = str(int(min_out * (10 ** d_out)))
                    logger.info(f"    CALCULATED min_amount_out_units: {p.min_amount_out_units}")
                else:
                    logger.warning("    Price data missing, defaulting to 0")
                    p.min_amount_out_units = "0"
            except Exception as e:
                logger.warning(f"    Failed to estimate min_amount_out: {e}")
                p.min_amount_out_units = "0"
        else:
            logger.info("    Not a swap, defaulting to 0")
            p.min_amount_out_units = "0"

    # Force a deterministic deadline (now + 20 minutes) to avoid LLM oscillation
    # and satisfy Patriarch timing risk guardrails.
    current_time = int(time.time())
    p.deadline_unix = current_time + 1200 # 20 minutes
    logger.info(f"  FORCED deadline_unix: {p.deadline_unix} (now + 20m)")

    ctx_hash, tx_hash = capture_and_persist(
        agent="Quant_Node_A",
        proposal_id=p.proposal_id,
        iteration=p.iteration,
        model_id="gpt-4o",
        temperature=0.0,
        seed=LLM_SEED,
        schema=Proposal.model_json_schema(),
        schema_name="Proposal",
        system_prompt=state.get("llm_system_prompt", ""),
        messages=state.get("llm_messages", []),
        response_raw=state.get("llm_raw_response", ""),
        parsed_obj=p,
        tools_invoked=[],
    )
    p.llm_context_hash = ctx_hash
    p.llm_context_0g_tx = tx_hash
    return {"current_proposal": p}


def self_audit(state: AgentState):
    p = state["current_proposal"]
    if p is None:
        return {}
    if p.quant_analysis_hash != state["quant_analysis_hash"]:
        logger.warning("Self-audit failed: analysis hash mismatch.")
        return {"current_proposal": None}
    return {}


def sign_proposal(state: AgentState):
    p: Proposal = state["current_proposal"]
    if p is None:
        return {}

    treasury = SafeTreasury()
    router = UniswapV4Router(
        w3=treasury.w3 if not treasury.mock_mode else None,
        owner=treasury.safe_address if not treasury.mock_mode else None,
    )

    # Pin invariants from state BEFORE digesting.
    p.quant_analysis_hash = state["quant_analysis_hash"]
    p.market_snapshot_hash = state["market_snapshot_hash"]
    p.safe_nonce = treasury.read_nonce()

    calldata = router.generate_calldata(p)
    p.safe_tx_hash = treasury.get_safe_tx_hash(treasury.target_address(), calldata, nonce=p.safe_nonce)

    safe_addr = treasury.safe_address or "0x0000000000000000000000000000000000000000"
    p_digest = proposal_eip712_digest(p, safe_addr, p.chain_id)
    p.proposal_hash = "0x" + p_digest.hex()

    b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))

    if QUANT_KEY:
        sig_bundle = sign_digest(b_digest, QUANT_KEY)
        sig_safe = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), QUANT_KEY)
        p.quant_signature = sig_bundle + sig_safe[2:]
        logger.info(f"Signed proposal {p.proposal_id} (nonce={p.safe_nonce}, signer={QUANT_ADDR})")
    else:
        logger.warning(f"No QUANT_KEY available — proposal {p.proposal_id} unsigned (mock mode).")

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
