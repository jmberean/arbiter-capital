import sqlite3
import json
import time
import os
import requests
import logging
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "axl_network.db")
logger = logging.getLogger("AXLNetwork")

class MockAXLNode:
    """
    Simulates a Gensyn AXL P2P node using a local SQLite database.
    Used for local development and testing.
    """
    def __init__(self, node_id: str, url_env: str = "AXL_NODE_URL"):
        self.node_id = node_id
        self.axl_url = os.getenv(url_env)
        self.use_live_axl = self.axl_url is not None
        self.demo_mode = os.getenv("DEMO_MODE") == "1"
        self._init_db()
        self._assert_demo_transport()
        
        if self.use_live_axl:
            logger.info(f"Node {node_id} initialized with LIVE AXL at {self.axl_url}")
        else:
            logger.info(f"Node {node_id} initialized in MOCK (SQLite) mode — DEV ONLY.")

    def _assert_demo_transport(self) -> None:
        """Fail-closed if DEMO_MODE=1 and we'd silently fall back to SQLite."""
        if self.demo_mode and not self.use_live_axl:
            logger.error(
                f"DEMO_MODE=1 but {self.node_id} has no AXL_NODE_URL set. "
                "SQLite mock is a centralized broker and violates the Gensyn bounty's "
                "'no centralized message brokers' requirement. Refusing to start."
            )
            import sys
            sys.exit(1)

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    payload TEXT,
                    sender TEXT,
                    timestamp REAL
                )
            ''')
            conn.commit()

    def publish(self, topic: str, payload: dict):
        """Broadcasts a payload to the AXL network."""
        if self.use_live_axl:
            try:
                # In real AXL, we send to specific peers or broadcast
                # Here we simulate the broadcast by sending to the local AXL bridge
                # The 'to' field would be a broadcast address or specific peer keys from .env
                peer_keys = os.getenv("AXL_PEER_KEYS", "").split(",")
                
                for peer in peer_keys:
                    if not peer: continue
                    logger.info(f"Publishing to AXL Peer: {peer[:8]}... on topic: {topic}")
                    requests.post(f"{self.axl_url}/send", json={
                        "to": peer,
                        "data": {"topic": topic, "payload": payload, "sender": self.node_id}
                    })
                
                # Also write to local DB for logging/visibility
                self._write_to_db(topic, payload)
                return
            except Exception as e:
                logger.error(f"Failed to publish to LIVE AXL: {e}. Falling back to SQLite.")

        self._write_to_db(topic, payload)

    def _write_to_db(self, topic: str, payload: dict):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (topic, payload, sender, timestamp) VALUES (?, ?, ?, ?)",
                (topic, json.dumps(payload), self.node_id, time.time())
            )
            conn.commit()

    def subscribe(self, topic: str, last_id: int = 0) -> List[Dict]:
        """Polls for new messages. In live mode, this could poll a /receive endpoint."""
        if self.use_live_axl:
            try:
                # Simulate polling the AXL node's message buffer
                response = requests.get(f"{self.axl_url}/receive?topic={topic}&last_id={last_id}")
                if response.status_code == 200:
                    return response.json().get("messages", [])
            except Exception:
                pass # Fall back to SQLite polling

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, payload, sender, timestamp FROM messages WHERE topic = ? AND id > ? ORDER BY id ASC",
                (topic, last_id)
            )
            rows = cursor.fetchall()
            return [{"id": r["id"], "payload": json.loads(r["payload"]), "sender": r["sender"]} for r in rows]

    def clear_network(self):
        """Clears the simulated network state."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM messages")
            conn.commit()
