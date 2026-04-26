import sqlite3
import json
import time
import os
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "axl_network.db")

class MockAXLNode:
    """
    Simulates a Gensyn AXL P2P node. 
    Uses a local SQLite database as a shared message broker to allow 
    physically separate Python processes to communicate.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._init_db()

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
        """Broadcasts a payload to the AXL network under a specific topic."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (topic, payload, sender, timestamp) VALUES (?, ?, ?, ?)",
                (topic, json.dumps(payload), self.node_id, time.time())
            )
            conn.commit()

    def subscribe(self, topic: str, last_id: int = 0) -> List[Dict]:
        """Polls the AXL network for new messages on a specific topic."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, payload, sender, timestamp FROM messages WHERE topic = ? AND id > ? ORDER BY id ASC",
                (topic, last_id)
            )
            rows = cursor.fetchall()
            return [{"id": r["id"], "payload": json.loads(r["payload"]), "sender": r["sender"]} for r in rows]

    def clear_network(self):
        """Clears the simulated network state (Useful for fresh test runs)."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM messages")
            conn.commit()
