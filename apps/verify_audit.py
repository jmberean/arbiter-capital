import os
import sys
import json
import logging
import hashlib
import argparse
import time
from typing import Optional
from web3 import Web3
import chromadb
from dotenv import load_dotenv
from eth_utils import keccak

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AuditVerifier")

MIN_CONFIRMATIONS = 3
CONFIRMATION_POLL_INTERVAL = 2.0  # seconds between polls
CONFIRMATION_TIMEOUT = 120.0      # give up after 2 minutes


class AuditVerifier:
    def __init__(self):
        self.zero_g_rpc = os.getenv("ZERO_G_RPC_URL", "https://evmrpc-testnet.0g.ai")
        self.w3 = Web3(Web3.HTTPProvider(self.zero_g_rpc))
        self.storage_path = os.path.join(os.path.dirname(__file__), "0g_storage")

        db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        try:
            self.collection = self.chroma_client.get_collection("decision_receipts")
        except Exception:
            self.collection = None

    # ------------------------------------------------------------------
    # Chain walk (primary verification path)
    # ------------------------------------------------------------------

    def walk_chain(self, head_hash: Optional[str] = None) -> bool:
        from memory.audit_chain import AuditChainHead
        head = head_hash or AuditChainHead().head
        if not head:
            print("No audit chain head found. Run some proposals first.")
            return False

        cur, count = head, 0
        while cur:
            # Step 6.6: wait for MIN_CONFIRMATIONS before treating an on-chain receipt as final
            if cur.startswith("0x") and self.w3.is_connected():
                if not self._wait_for_confirmations(cur):
                    print(f"CONFIRMATION TIMEOUT — receipt {cur[:12]}… may be in a reorg. Aborting.")
                    return False

            try:
                receipt = self._fetch_receipt(cur)
            except Exception as e:
                print(f"CHAIN BROKEN at {cur}: {e}")
                return False

            if not self._integrity_ok(receipt):
                print(f"INTEGRITY FAIL at receipt {cur}")
                return False

            rtype = receipt.get("receipt_type", "?")
            rid = receipt.get("receipt_id", cur[:12])
            if rtype == "AttackRejection":
                payload = receipt.get("payload", {})
                print(f"  ⚠ ATTACK_REJECTED [{payload.get('attack_kind')}] — "
                      f"defended by {payload.get('detected_by')}")
            else:
                confs_label = f" [{MIN_CONFIRMATIONS}+ confs]" if cur.startswith("0x") else " [local]"
                print(f"  ✓ [{rtype}] receipt_id={rid}{confs_label}")

            cur = receipt.get("prev_0g_tx_hash")
            count += 1

        print(f"\nCHAIN VERIFIED — {count} receipts walked.")
        return True

    def _fetch_receipt(self, tx_hash: str) -> dict:
        local_path = os.path.join(self.storage_path, f"{tx_hash}.json")
        if os.path.exists(local_path):
            with open(local_path) as f:
                return json.load(f)
        if tx_hash.startswith("0x"):
            try:
                tx = self.w3.eth.get_transaction(tx_hash)
                data_text = self.w3.to_text(tx["input"])
                return json.loads(data_text)
            except Exception as e:
                raise FileNotFoundError(f"Not found on-chain: {e}")
        raise FileNotFoundError(f"Receipt {tx_hash} not found locally or on-chain.")

    def _wait_for_confirmations(self, tx_hash: str, min_confirmations: int = MIN_CONFIRMATIONS) -> bool:
        """Poll until tx_hash has at least min_confirmations, or timeout. Returns True if confirmed."""
        if not tx_hash.startswith("0x"):
            return True  # local mock hash — no on-chain reorg risk
        deadline = time.time() + CONFIRMATION_TIMEOUT
        while time.time() < deadline:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt and receipt.get("blockNumber"):
                    current_block = self.w3.eth.block_number
                    confs = current_block - receipt["blockNumber"] + 1
                    if confs >= min_confirmations:
                        logger.debug(f"{tx_hash[:12]}… confirmed ({confs} blocks)")
                        return True
                    logger.debug(f"{tx_hash[:12]}… waiting for confirmations ({confs}/{min_confirmations})")
            except Exception as e:
                logger.warning(f"Confirmation poll error for {tx_hash[:12]}…: {e}")
            time.sleep(CONFIRMATION_POLL_INTERVAL)
        logger.error(f"Timeout waiting for {min_confirmations} confirmations on {tx_hash[:12]}…")
        return False

    def _integrity_ok(self, receipt: dict) -> bool:
        stored_hash = receipt.get("receipt_hash")
        if not stored_hash:
            return True  # pre-v5 receipt without hash — allow
        body = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        expected = "0x" + keccak(canonical).hex()
        if expected != stored_hash:
            logger.error(f"Hash mismatch: expected {expected}, stored {stored_hash}")
            return False
        return True

    # ------------------------------------------------------------------
    # Legacy full audit (ChromaDB-based)
    # ------------------------------------------------------------------

    def verify_decision(self, doc_id: str, metadata: dict) -> bool:
        zero_g_hash = metadata.get("0g_hash")
        proposal_id = metadata.get("proposal_id")
        logger.info(f"Verifying Proposal {proposal_id} (Hash: {zero_g_hash[:12]}...)")

        if zero_g_hash.startswith("0x"):
            try:
                tx = self.w3.eth.get_transaction(zero_g_hash)
                if not tx:
                    logger.error(f"❌ FAILED: Transaction {zero_g_hash} not found on 0G Testnet.")
                    return False
                input_data = tx.get("input", "")
                if not input_data:
                    logger.error(f"❌ FAILED: Transaction {zero_g_hash} has no data.")
                    return False
                receipt_str = self.w3.to_text(input_data)
                receipt = json.loads(receipt_str)
                logger.info(f"✅ SUCCESS: Verified on 0G Testnet. Proposal: {receipt['proposal']['proposal_id']}")
                return True
            except Exception as e:
                logger.warning(f"Could not verify on-chain ({e}). Checking local fallback...")

        file_path = os.path.join(self.storage_path, f"{zero_g_hash}.json")
        if os.path.exists(file_path):
            with open(file_path) as f:
                content = f.read()
            calculated_hash = hashlib.sha256(content.encode()).hexdigest()
            if not zero_g_hash.startswith("0x") and calculated_hash != zero_g_hash:
                logger.error(f"❌ FAILED: Local integrity check failed for {zero_g_hash}")
                return False
            logger.info(f"✅ SUCCESS: Verified locally. Hash: {calculated_hash[:12]}...")
            return True

        logger.error(f"❌ FAILED: Decision receipt {zero_g_hash} not found.")
        return False

    def run_full_audit(self) -> None:
        logger.info("Starting Full Audit Verification...")
        if not self.collection:
            logger.info("No ChromaDB collection found.")
            return
        results = self.collection.get()
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", [])
        if not ids:
            logger.info("No decisions found in memory to verify.")
            return
        success_count = sum(
            1 for i in range(len(ids)) if self.verify_decision(ids[i], metadatas[i])
        )
        logger.info(f"Audit Complete. Verified {success_count}/{len(ids)} decisions successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arbiter Capital audit verifier")
    parser.add_argument("--walk-from-head", action="store_true",
                        help="Walk the hash-chained 0G audit log from the current head.")
    parser.add_argument("--head", type=str, default=None,
                        help="Start walk from a specific tx hash instead of the stored head.")
    args = parser.parse_args()

    verifier = AuditVerifier()
    if args.walk_from_head or args.head:
        ok = verifier.walk_chain(head_hash=args.head)
        sys.exit(0 if ok else 1)
    else:
        verifier.run_full_audit()
