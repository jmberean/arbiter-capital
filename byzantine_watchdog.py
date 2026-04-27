import time
import logging
import json
import random
import os
from dotenv import load_dotenv
from core.network import MockAXLNode
from core.models import Proposal, ConsensusStatus, ActionType
from core.crypto import sign_digest, proposal_eip712_digest, bundle_hash
from core.identity import QUANT_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ByzantineWatchdog")

class ByzantineWatchdog:
    def __init__(self):
        self.axl_node = MockAXLNode(node_id="Adversary_Node_Z", url_env="AXL_NODE_URL_WATCHDOG")
        self.target_safe = os.getenv("SAFE_ADDRESS", "0x0")

    def forge_proposal_invalid_math(self):
        """Attacks the Patriarch by claiming a false analysis hash."""
        logger.info("⚔️ ATTACK: Forging proposal with fake quant_analysis_hash...")
        p = Proposal(
            proposal_id=f"attack_math_{int(time.time())}",
            target_protocol="Uniswap_V4",
            action=ActionType.SWAP,
            asset_in="WETH",
            asset_out="USDC",
            amount_in=1.0,
            rationale="Trust me, the math is good.",
            quant_analysis_hash="0x" + "f"*64, # Fake hash
            safe_tx_hash="0x" + "0"*64,
            consensus_status=ConsensusStatus.PENDING
        )
        self.axl_node.publish(topic="PROPOSALS", payload=p.model_dump())

    def replay_nonce_attack(self):
        """Attacks the Execution Node by replaying an old safe_nonce."""
        logger.info("⚔️ ATTACK: Replaying an old safe_nonce...")
        # In a real attack, we'd grab a signed msg from the history
        pass

    def mutate_signed_json(self):
        """Attacks the network by changing the 'amount_in' after Quant signed it."""
        logger.info("⚔️ ATTACK: Mutating signed JSON (Bumping amount)...")
        # 1. Create a valid proposal and sign it
        p = Proposal(
            proposal_id=f"attack_mutate_{int(time.time())}",
            target_protocol="Uniswap_V4",
            action=ActionType.SWAP,
            asset_in="WETH",
            asset_out="USDC",
            amount_in=1.0,
            rationale="Legit trade.",
            safe_tx_hash="0x" + "1"*64,
            consensus_status=ConsensusStatus.PENDING
        )
        
        # Quant signs for 1.0 WETH
        if QUANT_KEY:
            p_digest = proposal_eip712_digest(p.model_dump(by_alias=True), self.target_safe, p.chain_id)
            b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
            sig_bundle = sign_digest(b_digest, QUANT_KEY)
            sig_safe   = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), QUANT_KEY)
            p.quant_signature = sig_bundle + sig_safe[2:]
            
            # 2. MUTATE the payload! Change 1.0 -> 100.0
            p_dict = p.model_dump()
            p_dict["amount_in"] = 100.0
            p_dict["amount_in_units"] = str(int(100.0 * 1e18))
            
            logger.info(f"Published mutated proposal {p.proposal_id} (Signed for 1.0, claimed 100.0)")
            self.axl_node.publish(topic="PROPOSALS", payload=p_dict)

    def run_chaos_loop(self):
        logger.info("Byzantine Watchdog active. Starting chaos loop...")
        attacks = [self.forge_proposal_invalid_math, self.mutate_signed_json]
        while True:
            attack = random.choice(attacks)
            attack()
            time.sleep(30)

if __name__ == "__main__":
    load_dotenv()
    watchdog = ByzantineWatchdog()
    watchdog.run_chaos_loop()
