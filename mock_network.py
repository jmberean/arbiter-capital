import logging
import time
import uuid
import os
from dotenv import load_dotenv
from core.market_god import generate_market_data
from core.models import Proposal, ConsensusStatus
from agents.quant import quant_app
from agents.patriarch import patriarch_app
from execution.firewall import PolicyFirewall
from langchain_core.messages import HumanMessage

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MockNetwork")

def run_simulation(scenario: str = "normal"):
    logger.info(f"--- STARTING SIMULATION SCENARIO: {scenario.upper()} ---")
    
    # 1. Inject Market Data
    logger.info("1. Generating Market Data...")
    market_data = generate_market_data(scenario)
    
    # 2. Quant Agent formulates proposal
    logger.info("2. Triggering Quant Agent (Process 1)...")
    quant_state = {
        "market_data": market_data,
        "messages": [],
        "iteration": 0
    }
    
    quant_result = quant_app.invoke(quant_state)
    proposal: Proposal = quant_result.get("current_proposal")
    
    if not proposal:
        logger.info("Simulation ended: Quant agent determined no action is necessary.")
        return

    # Ensure proposal has an ID
    if not proposal.proposal_id or proposal.proposal_id == "uuid_placeholder":
        proposal.proposal_id = f"prop_{uuid.uuid4().hex[:8]}"

    logger.info(f"Quant drafted Proposal: {proposal.action.value} {proposal.amount_in} {proposal.asset_in} to {proposal.asset_out}")
    logger.info("--- TRANSMITTING OVER MOCK AXL NETWORK ---")
    time.sleep(1) # Simulate network delay

    # 3. Patriarch Agent evaluates proposal
    logger.info("3. Triggering Patriarch Agent (Process 2)...")
    patriarch_state = {
        "incoming_proposal": proposal,
        "messages": []
    }
    
    patriarch_result = patriarch_app.invoke(patriarch_state)
    reviewed_proposal: Proposal = patriarch_result.get("reviewed_proposal")
    
    if not reviewed_proposal:
        logger.error("Simulation failed: Patriarch returned no proposal.")
        return
        
    logger.info(f"Patriarch evaluation complete. Consensus Status: {reviewed_proposal.consensus_status.value}")
    logger.info(f"Patriarch Rationale: {reviewed_proposal.rationale}")

    # 4. Handle Consensus and Firewall Routing
    if reviewed_proposal.consensus_status == ConsensusStatus.ACCEPTED:
        logger.info("Consensus REACHED. Routing to Execution Node (Process 3)...")
        time.sleep(1)
        
        firewall = PolicyFirewall()
        try:
            is_cleared = firewall.validate_proposal(reviewed_proposal)
            if is_cleared:
                logger.info("🔥 FIREWALL PASSED. Ready for KeeperHub routing.")
                # TODO: In MVP3, route to KeeperHub here
        except ValueError as e:
            logger.error(f"❌ FIREWALL REJECTED: {e}")
            
    elif reviewed_proposal.consensus_status == ConsensusStatus.REJECTED:
        logger.warning("Consensus FAILED. Proposal rejected by Patriarch.")
        # In a real scenario, this would loop back to the Quant for revision.
        
    logger.info("--- SIMULATION COMPLETE ---")


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
         logger.error("CRITICAL: ANTHROPIC_API_KEY environment variable is not set.")
         exit(1)
         
    # Run the flash crash scenario
    run_simulation("flash_crash_eth")
