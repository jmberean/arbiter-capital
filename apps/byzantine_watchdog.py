"""
DEMO-ONLY 5th process. Publishes a scripted sequence of six Byzantine attacks on the AXL bus.
Every attack is expected to be rejected and forensically logged by the defenders.

Usage:
  python byzantine_watchdog.py --attack A1          # single attack
  python byzantine_watchdog.py --attack-sequence    # all 6 in order, 4s apart
  python byzantine_watchdog.py                      # random loop (dev)
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sqlite3
import time

from dotenv import load_dotenv
from eth_account import Account

from core.crypto import (
    proposal_eip712_digest, bundle_hash, sign_digest, sim_result_digest,
)
from core.dedupe import DedupeLedger
from core.models import (
    Proposal, ConsensusMessage, ConsensusStatus, ActionType, SimulationResult,
)
from core.network import MockAXLNode
from core.persistence import STATE_DIR

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ByzantineWatchdog")

# Attacker key: NOT a Safe owner — any unsigned/random key is fine for the demo.
_RAW = os.getenv("ATTACKER_PRIVATE_KEY")
if _RAW:
    ATTACKER_KEY = bytes.fromhex(_RAW[2:] if _RAW.startswith("0x") else _RAW)
else:
    ATTACKER_KEY = Account.create().key
ATTACKER_ADDR = Account.from_key(ATTACKER_KEY).address

TARGET_SAFE = os.getenv("SAFE_ADDRESS", "0x0000000000000000000000000000000000000000")


def _base_proposal(suffix: str) -> Proposal:
    """Minimal syntactically valid proposal for forging."""
    return Proposal(
        proposal_id=f"attack_{suffix}_{int(time.time())}",
        target_protocol="Uniswap_V4",
        action=ActionType.SWAP,
        asset_in="WETH",
        asset_out="USDC",
        amount_in=1.0,
        rationale="Adversarial payload.",
        consensus_status=ConsensusStatus.PENDING,
        safe_tx_hash="0x" + "aa" * 32,
        chain_id=11155111,
    )


def _last_executed_record() -> tuple[str, int, str] | None:
    """Pull the most recently executed (safe_address, safe_nonce, proposal_id)
    from the dedupe ledger so A2's replay actually targets a real settlement."""
    path = STATE_DIR / "executed_proposals.sqlite"
    if not path.exists():
        return None
    try:
        with sqlite3.connect(path) as c:
            row = c.execute(
                "SELECT safe_address, safe_nonce, proposal_id FROM executed ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            return row
    except sqlite3.Error:
        return None


class ByzantineWatchdog:
    def __init__(self):
        self.node = MockAXLNode(node_id="Adversary_Node_Z", url_env="AXL_NODE_URL_WATCHDOG")

    # ------------------------------------------------------------------
    # A1: INVALID_SIGNATURE — garbage quant_signature
    # Defender: Patriarch (recover_signer != QUANT_ADDR)
    # ------------------------------------------------------------------
    def attack_A1_invalid_sig(self):
        logger.info("⚔️  A1 INVALID_SIGNATURE — proposal with garbage signature")
        p = _base_proposal("A1")
        p.quant_signature = "0x" + "00" * 65 + "ff" * 65
        self.node.publish("PROPOSALS", p.model_dump())

    # ------------------------------------------------------------------
    # A2: REPLAY_NONCE — reuse a real settled (proposal_id, nonce, safe_tx_hash)
    # Defender: Execution Node (DedupeLedger.already_executed → skip + EXECUTION_FAILURE)
    # ------------------------------------------------------------------
    def attack_A2_replay_nonce(self):
        logger.info("⚔️  A2 REPLAY_NONCE — replaying old consensus signatures for a settled nonce")
        rec = _last_executed_record()
        if not rec:
            logger.warning(
                "A2: no prior settlement found in dedupe ledger; falling back to synthetic replay. "
                "Run a real proposal first to make this attack land properly."
            )
            safe_address = TARGET_SAFE
            safe_nonce = 0
            proposal_id = "prop_replay_synthetic"
            safe_tx_hash = "0x" + "aa" * 32
        else:
            safe_address, safe_nonce, proposal_id = rec
            safe_tx_hash = "0x" + "ab" * 32

        # Re-emit a CONSENSUS_SIGNATURES message claiming Patriarch's role
        # but signing with the attacker key — execution node should still
        # detect the proposal_id as already settled and reject.
        attacker_sig = sign_digest(bytes.fromhex(safe_tx_hash[2:]), ATTACKER_KEY)
        fake_msg = ConsensusMessage(
            proposal_id=proposal_id,
            iteration=1,
            signer_id="Adversary_Node_Z",
            signer_address=ATTACKER_ADDR,
            signature=attacker_sig,
            safe_tx_hash=safe_tx_hash,
            timestamp=time.time(),
        )
        self.node.publish("CONSENSUS_SIGNATURES", fake_msg.model_dump())

    # ------------------------------------------------------------------
    # A3: MATH_FORGE — mutated risk_score with stale quant_analysis_hash
    # Defender: Patriarch deterministic_recheck → MATH_MISMATCH
    # ------------------------------------------------------------------
    def attack_A3_math_forge(self):
        logger.info("⚔️  A3 MATH_FORGE — proposal with mutated risk_score, stale analysis hash")
        p = _base_proposal("A3")
        p.risk_score_bps = 50
        p.quant_analysis_hash = "0x" + "f" * 64
        p_digest = proposal_eip712_digest(p, TARGET_SAFE, p.chain_id)
        b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
        sig_bundle = sign_digest(b_digest, ATTACKER_KEY)
        sig_safe = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), ATTACKER_KEY)
        p.quant_signature = sig_bundle + sig_safe[2:]
        self.node.publish("PROPOSALS", p.model_dump())

    # ------------------------------------------------------------------
    # A4: WHITELIST_BYPASS — non-whitelisted asset_in
    # Defender: Patriarch firewall WHITELIST_VIOLATION
    # ------------------------------------------------------------------
    def attack_A4_whitelist_bypass(self):
        logger.info("⚔️  A4 WHITELIST_BYPASS — asset_in='DOGE' not in whitelist")
        p = _base_proposal("A4")
        p.asset_in = "DOGE"
        p.asset_in_decimals = 8
        p.amount_in_units = str(int(1.0 * 10**8))
        p_digest = proposal_eip712_digest(p, TARGET_SAFE, p.chain_id)
        b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
        sig_bundle = sign_digest(b_digest, ATTACKER_KEY)
        sig_safe = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), ATTACKER_KEY)
        p.quant_signature = sig_bundle + sig_safe[2:]
        self.node.publish("PROPOSALS", p.model_dump())

    # ------------------------------------------------------------------
    # A5: FAKE_SIM_RESULT — unsigned/forged SimulationResult
    # Defender: Patriarch (simulator_signature ∉ ATTESTORS)
    # ------------------------------------------------------------------
    def attack_A5_fake_sim_result(self):
        logger.info("⚔️  A5 FAKE_SIM_RESULT — unsigned/forged simulation result")
        forged_digest = sim_result_digest(
            proposal_id="prop_any", iteration=1, success=True,
            gas_used=100000, return_data="0x", fork_block=0,
        )
        # Sign with attacker key — recovers to ATTACKER_ADDR ∉ ATTESTORS
        forged_sig = sign_digest(forged_digest, ATTACKER_KEY)
        fake = SimulationResult(
            request_id="forged_req_A5",
            proposal_id="prop_any",
            success=True,
            gas_used=100000,
            return_data="0x",
            revert_reason=None,
            fork_block=0,
            simulator_signature=forged_sig,
            attestor_address=ATTACKER_ADDR,
            timestamp=time.time(),
        )
        self.node.publish("SIM_ORACLE_RESULT", fake.model_dump())

    # ------------------------------------------------------------------
    # A6: WRONG_DOMAIN — chain_id=1 (mainnet) instead of Sepolia
    # Defender: Patriarch — EIP-712 domain mismatch breaks recovery
    # ------------------------------------------------------------------
    def attack_A6_wrong_domain(self):
        logger.info("⚔️  A6 WRONG_DOMAIN — proposal with chain_id=1 (mainnet)")
        p = _base_proposal("A6")
        p.chain_id = 1
        p_digest = proposal_eip712_digest(p, TARGET_SAFE, p.chain_id)
        b_digest = bundle_hash(p_digest, bytes.fromhex(p.safe_tx_hash[2:]))
        sig_bundle = sign_digest(b_digest, ATTACKER_KEY)
        sig_safe = sign_digest(bytes.fromhex(p.safe_tx_hash[2:]), ATTACKER_KEY)
        p.quant_signature = sig_bundle + sig_safe[2:]
        self.node.publish("PROPOSALS", p.model_dump())

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    ATTACK_MAP = {
        "A1": "attack_A1_invalid_sig",
        "A2": "attack_A2_replay_nonce",
        "A3": "attack_A3_math_forge",
        "A4": "attack_A4_whitelist_bypass",
        "A5": "attack_A5_fake_sim_result",
        "A6": "attack_A6_wrong_domain",
    }

    def run_attack(self, attack_id: str):
        method_name = self.ATTACK_MAP.get(attack_id.upper())
        if not method_name:
            logger.error(f"Unknown attack id: {attack_id}. Valid: {list(self.ATTACK_MAP)}")
            return
        getattr(self, method_name)()

    def run_sequence(self, delay: float = 4.0):
        logger.info(f"Starting scripted attack sequence (A1→A6, {delay}s apart)...")
        for attack_id in ["A1", "A2", "A3", "A4", "A5", "A6"]:
            self.run_attack(attack_id)
            logger.info(f"Fired {attack_id}. Waiting {delay}s...")
            time.sleep(delay)
        logger.info("Scripted attack sequence complete.")

    def run_chaos_loop(self):
        logger.info("Byzantine Watchdog active. Starting random chaos loop...")
        attacks = list(self.ATTACK_MAP.keys())
        while True:
            self.run_attack(random.choice(attacks))
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Byzantine Watchdog — adversarial AXL agent")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--attack", type=str, help="Fire a single attack (A1–A6)")
    group.add_argument("--attack-sequence", action="store_true",
                       help="Fire all 6 attacks in order, 4s apart")
    parser.add_argument("--delay", type=float, default=4.0,
                        help="Seconds between attacks in sequence mode (default 4)")
    args = parser.parse_args()

    watchdog = ByzantineWatchdog()
    if args.attack:
        watchdog.run_attack(args.attack)
    elif args.attack_sequence:
        watchdog.run_sequence(delay=args.delay)
    else:
        watchdog.run_chaos_loop()
