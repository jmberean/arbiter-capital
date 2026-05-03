import time
import logging
import json
import uuid
import os
from dotenv import load_dotenv
load_dotenv()  # must run before core.identity is imported so keys are available at eval time
from core.network import MockAXLNode
from core.models import Proposal, ConsensusStatus, ConsensusMessage
from core.identity import QUANT_ADDR
from agents.quant import quant_app
from execution.safe_treasury import SafeTreasury
from execution.uniswap_v4.router import UniswapV4Router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantProcess")


def _quant_consensus_msg(proposal: Proposal) -> ConsensusMessage | None:
    """Extract the Quant's safe-tx signature from the proposal and wrap in ConsensusMessage."""
    if not proposal.quant_signature or not proposal.safe_tx_hash:
        return None
    # quant_signature = "0x" + sig_bundle_hex(130) + sig_safe_hex(130)
    sig_safe = "0x" + proposal.quant_signature[132:]
    return ConsensusMessage(
        proposal_id=proposal.proposal_id,
        iteration=proposal.iteration,
        signer_id="Quant_Node_A",
        signer_address=QUANT_ADDR,
        signature=sig_safe,
        safe_tx_hash=proposal.safe_tx_hash,
        timestamp=time.time(),
    )


def run_quant_daemon():
    logger.info("Initializing Quant Process (Node A)...")
    axl_node = MockAXLNode(node_id="Quant_Node_A", url_env="AXL_NODE_URL_QUANT")
    treasury = SafeTreasury()
    router = UniswapV4Router()

    last_market_id = 0
    last_feedback_id = 0
    proposal_history = {}

    logger.info("Quant listening for Market Data and Patriarch Feedback...")
    axl_node.publish("HEARTBEAT", {"node_id": "Quant_Node_A", "role": "quant", "timestamp": time.time(), "status": "ready"})

    while True:
        try:
            # 1. New market data
            market_messages = axl_node.subscribe(topic="MARKET_DATA", last_id=last_market_id)
            for msg in market_messages:
                last_market_id = msg["id"]
                market_data = msg["payload"]
                logger.info(f"Received market data from {msg['sender']}. Analyzing...")

                state = {"market_data": market_data, "messages": [], "iteration": 0}
                result = quant_app.invoke(state)
                proposal: Proposal = result.get("current_proposal")

                if proposal:
                    # Publish the market snapshot so the Patriarch can recompute
                    axl_node.publish(topic="MARKET_SNAPSHOTS", payload={
                        "market_snapshot_hash": result.get("market_snapshot_hash") or proposal.market_snapshot_hash,
                        "market_data": market_data,
                    })

                    logger.info(f"Publishing Proposal {proposal.proposal_id} to AXL Network...")
                    axl_node.publish(topic="PROPOSALS", payload=proposal.model_dump())

                    # Publish Quant's own consensus signature so Execution Node can collect it
                    cmsg = _quant_consensus_msg(proposal)
                    if cmsg:
                        axl_node.publish(topic="CONSENSUS_SIGNATURES", payload=cmsg.model_dump())
                        logger.info(f"Published Quant CONSENSUS_SIGNATURE for {proposal.proposal_id}")

                    proposal_history[proposal.proposal_id] = {
                        "market_data": market_data,
                        "iteration": result.get("iteration", 1),
                        "messages": result.get("messages", []),
                    }
                else:
                    logger.info("No actionable trade identified.")

            # 2. Patriarch feedback (rejections → iterate)
            feedback_messages = axl_node.subscribe(topic="PROPOSAL_EVALUATIONS", last_id=last_feedback_id)
            for msg in feedback_messages:
                last_feedback_id = msg["id"]
                evaluation = msg["payload"]

                if evaluation["consensus_status"] == ConsensusStatus.REJECTED.value:
                    prop_id = evaluation["proposal_id"]
                    logger.warning(f"Quant received REJECTION for {prop_id}. Rationale: {evaluation['rationale']}")

                    if prop_id in proposal_history:
                        history = proposal_history[prop_id]
                        if history["iteration"] < 3:
                            logger.info(f"Iterating on {prop_id} based on Patriarch feedback...")
                            state = {
                                "market_data": history["market_data"],
                                "messages": history["messages"],
                                "iteration": history["iteration"],
                                "patriarch_feedback": evaluation["rationale"],
                                "proposal_id": f"{prop_id}_v{history['iteration'] + 1}"
                            }
                            result = quant_app.invoke(state)
                            new_proposal: Proposal = result.get("current_proposal")

                            if new_proposal:
                                axl_node.publish(topic="MARKET_SNAPSHOTS", payload={
                                    "market_snapshot_hash": result.get("market_snapshot_hash") or new_proposal.market_snapshot_hash,
                                    "market_data": history["market_data"],
                                })

                                axl_node.publish(topic="PROPOSALS", payload=new_proposal.model_dump())

                                cmsg = _quant_consensus_msg(new_proposal)
                                if cmsg:
                                    axl_node.publish(topic="CONSENSUS_SIGNATURES", payload=cmsg.model_dump())

                                proposal_history[new_proposal.proposal_id] = {
                                    "market_data": history["market_data"],
                                    "iteration": result.get("iteration", history["iteration"] + 1),
                                    "messages": result.get("messages", []),
                                }
                            else:
                                logger.info("Quant conceded after feedback. No revised proposal.")
                        else:
                            logger.error(f"Max iterations reached for {prop_id}. Stopping negotiation.")

            time.sleep(2)

        except KeyboardInterrupt:
            logger.info("Quant Process shutting down.")
            break
        except Exception as e:
            logger.error(f"Error in Quant daemon: {e}")
            time.sleep(5)


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("CRITICAL: OPENAI_API_KEY environment variable is not set.")
        exit(1)
    run_quant_daemon()
