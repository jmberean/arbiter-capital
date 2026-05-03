"""
Gensyn AXL transport with optional envelope signing.

Per spec §3.3, every message published on the bus is wrapped in an AXLEnvelope
and signed by the producer's node key. Subscribers verify the producer
signature before unwrapping the payload, so a Byzantine peer cannot forge
`producer_node_id`.

When no AXL_NODE_KEY is configured, envelope signing is skipped (dev mode);
the demo gate (`DEMO_MODE=1`) still requires real AXL transport but does not
hard-require signed envelopes — sigs are advisory in this transport layer.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional

import requests
from eth_account import Account
from eth_utils import keccak

from core.crypto import envelope_digest, sign_digest, recover_signer

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "axl_network.db")
logger = logging.getLogger("AXLNetwork")

# Topics that warrant INFO-level logging when received (aids diagnosis)
_IMPORTANT_TOPICS = {"PROPOSALS", "FIREWALL_CLEARED", "CONSENSUS_SIGNATURES", "EXECUTION_SUCCESS"}


def _load_node_key() -> Optional[bytes]:
    """Load this node's secp256k1 key from AXL_NODE_KEY (preferred) or
    QUANT/PATRIARCH/EXECUTOR keys if AXL_NODE_KEY is unset."""
    raw = os.getenv("AXL_NODE_KEY") or os.getenv("EXECUTOR_PRIVATE_KEY")
    if not raw or raw.startswith("0xabc"):
        return None
    try:
        return bytes.fromhex(raw[2:] if raw.startswith("0x") else raw)
    except ValueError:
        return None


class MockAXLNode:
    """Gensyn AXL P2P node bridge.

    When AXL_NODE_URL_* is set (DEMO_MODE=1), messages are sent via the axl-node
    HTTP API (/send with X-Destination-Peer-Id header, /recv for polling).
    AXL is point-to-point; publish broadcasts to all peers in AXL_PEER_KEYS.
    Received messages are buffered in _inbox keyed by topic so multi-topic
    daemons don't lose messages across subscribe() calls.

    Falls back to SQLite when no AXL URL is configured (dev mode).
    """

    def __init__(self, node_id: str, url_env: str = "AXL_NODE_URL"):
        self.node_id = node_id
        self.axl_url = os.getenv(url_env)
        self.use_live_axl = self.axl_url is not None
        self.demo_mode = os.getenv("DEMO_MODE") == "1"
        self._inbox: Dict[str, List[Dict]] = {}
        self._inbox_lock = threading.Lock()
        self._drain_stop_evt = threading.Event()

        self._node_key = _load_node_key()
        self._node_addr = (
            Account.from_key(self._node_key).address if self._node_key else None
        )
        self._node_pubkey = (
            "0x" + Account.from_key(self._node_key)._key_obj.public_key.to_hex()[2:]
            if self._node_key else ""
        )

        self._init_db()
        self._assert_demo_transport()

        if self.use_live_axl:
            logger.info(f"Node {node_id} initialized with LIVE AXL at {self.axl_url}")
            self._start_background_drain()
        else:
            logger.info(f"Node {node_id} initialized in MOCK (SQLite) mode — DEV ONLY.")
        if self._node_key is None:
            logger.warning(f"Node {node_id}: no AXL_NODE_KEY — envelopes will be UNSIGNED.")

    # ------------------------------------------------------------------
    # Demo gate
    # ------------------------------------------------------------------
    def _assert_demo_transport(self) -> None:
        if self.demo_mode and not self.use_live_axl:
            logger.error(
                f"DEMO_MODE=1 but {self.node_id} has no AXL_NODE_URL set. "
                "SQLite mock is a centralized broker and violates the Gensyn bounty's "
                "'no centralized message brokers' requirement. Refusing to start."
            )
            import sys
            sys.exit(1)

    # ------------------------------------------------------------------
    # SQLite scaffolding (dev fallback)
    # ------------------------------------------------------------------
    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    payload TEXT,
                    sender TEXT,
                    timestamp REAL,
                    envelope TEXT
                )
            ''')
            # Older schemas without `envelope` column — additive migration
            cols = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
            if "envelope" not in cols:
                try:
                    conn.execute("ALTER TABLE messages ADD COLUMN envelope TEXT")
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    # ------------------------------------------------------------------
    # Envelope signing
    # ------------------------------------------------------------------
    def _build_envelope(self, topic: str, payload: dict) -> dict:
        ts = time.time()
        envelope = {
            "topic": topic,
            "producer_node_id": self.node_id,
            "producer_pubkey": self._node_pubkey,
            "timestamp": ts,
            "payload": payload,
            "producer_signature": "",
        }
        if self._node_key is not None:
            digest = envelope_digest(topic, payload, ts, self.node_id)
            envelope["producer_signature"] = sign_digest(digest, self._node_key)
        return envelope

    def _verify_envelope(self, envelope: dict) -> bool:
        """Best-effort check. Returns True if no sig is present (dev path) or
        if the signature recovers to a non-zero address. Recovery to a
        registered identity is enforced at the application layer
        (e.g., patriarch_process verifies QUANT_ADDR), not here."""
        sig = envelope.get("producer_signature")
        if not sig:
            return True
        try:
            digest = envelope_digest(
                envelope["topic"],
                envelope["payload"],
                float(envelope["timestamp"]),
                envelope["producer_node_id"],
            )
            recovered = recover_signer(digest, sig)
            return recovered != "0x0000000000000000000000000000000000000000"
        except Exception as e:
            logger.warning(f"Envelope verification error: {e}")
            return False

    # ------------------------------------------------------------------
    # Publish / subscribe
    # ------------------------------------------------------------------
    def publish(self, topic: str, payload: dict):
        envelope = self._build_envelope(topic, payload)

        if self.use_live_axl:
            peer_keys = [k for k in os.getenv("AXL_PEER_KEYS", "").split(",") if k]
            if not peer_keys:
                logger.warning(f"AXL_PEER_KEYS not set — {topic} will not be delivered over AXL.")
            else:
                msg_bytes = json.dumps({
                    "topic": topic,
                    "payload": payload,
                    "sender": self.node_id,
                    "envelope": envelope,
                }).encode()
                sent = 0
                for peer in peer_keys:
                    try:
                        r = requests.post(
                            f"{self.axl_url}/send",
                            data=msg_bytes,
                            headers={"X-Destination-Peer-Id": peer},
                            timeout=5,
                        )
                        if r.status_code == 200:
                            sent += 1
                    except Exception as e:
                        logger.warning(f"AXL send to {peer[:12]}... failed: {e}")
                logger.info(f"AXL publish: topic={topic} sent_to={sent}/{len(peer_keys)} peers")
                return

        self._write_to_db(topic, payload, envelope)

    def _write_to_db(self, topic: str, payload: dict, envelope: dict):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (topic, payload, sender, timestamp, envelope) VALUES (?, ?, ?, ?, ?)",
                (topic, json.dumps(payload), self.node_id, time.time(), json.dumps(envelope)),
            )
            conn.commit()

    def _drain_axl_inbox(self) -> None:
        """Pull all pending messages from /recv into per-topic buffers."""
        while True:
            try:
                r = requests.get(f"{self.axl_url}/recv", timeout=2)
                if r.status_code == 204:
                    break
                if r.status_code == 200:
                    data = json.loads(r.content)
                    msg_topic = data.get("topic")
                    if not msg_topic:
                        logger.debug("AXL recv: message has no topic, skipping")
                        continue
                    msg = {
                        "id": int(time.time() * 1000),
                        "payload": data.get("payload", {}),
                        "sender": data.get("sender", r.headers.get("X-From-Peer-Id", "")),
                        "envelope": data.get("envelope", {}),
                    }
                    verified = self._verify_envelope(msg["envelope"])
                    level = logging.INFO if msg_topic in _IMPORTANT_TOPICS else logging.DEBUG
                    logger.log(level, "AXL recv: topic=%s sender=%s verified=%s",
                               msg_topic, msg.get("sender", "?")[:16], verified)
                    if verified:
                        with self._inbox_lock:
                            self._inbox.setdefault(msg_topic, []).append(msg)
                    else:
                        logger.warning("AXL recv: dropping unverified message topic=%s sender=%s",
                                       msg_topic, msg.get("sender", "?")[:16])
            except Exception as e:
                logger.warning("AXL drain error: %s", e)
                break

    def _start_background_drain(self) -> None:
        """Continuously drain the AXL /recv queue in a background thread.

        This ensures messages are captured the moment they arrive, even when
        the main processing loop is blocked inside a long LangGraph call.
        Without this, messages with short AXL TTLs expire before the next
        subscribe() poll cycle.
        """
        def _loop():
            while not self._drain_stop_evt.is_set():
                try:
                    self._drain_axl_inbox()
                except Exception as e:
                    logger.warning("Background drain error: %s", e)
                self._drain_stop_evt.wait(0.5)

        t = threading.Thread(target=_loop, daemon=True, name=f"axl-drain-{self.node_id}")
        t.start()
        logger.info(f"AXL background drain thread started for {self.node_id}")

    def subscribe(self, topic: str, last_id: int = 0) -> List[Dict]:
        if self.use_live_axl:
            try:
                with self._inbox_lock:
                    return self._inbox.pop(topic, [])
            except Exception as e:
                logger.warning(f"AXL subscribe failed: {e}. Falling back to SQLite.")

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, payload, sender, timestamp, envelope FROM messages "
                "WHERE topic = ? AND id > ? ORDER BY id ASC",
                (topic, last_id),
            )
            rows = cursor.fetchall()

        result = []
        for r in rows:
            envelope = json.loads(r["envelope"]) if r["envelope"] else {}
            if envelope and not self._verify_envelope(envelope):
                logger.warning(f"Rejecting message {r['id']} — bad envelope sig.")
                continue
            result.append({
                "id": r["id"],
                "payload": json.loads(r["payload"]),
                "sender": r["sender"],
                "envelope": envelope,
            })
        return result

    def clear_network(self):
        if self.use_live_axl:
            with self._inbox_lock:
                self._inbox.clear()
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM messages")
            conn.commit()
