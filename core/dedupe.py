import sqlite3, time
from core.persistence import STATE_DIR

class DedupeLedger:
    def __init__(self):
        self.path = STATE_DIR / "executed_proposals.sqlite"
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS executed (
                safe_address TEXT, safe_nonce INTEGER, proposal_id TEXT,
                tx_hash TEXT, status TEXT, ts REAL,
                PRIMARY KEY (safe_address, safe_nonce))""")

    def already_executed(self, safe_address: str, safe_nonce: int) -> bool:
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT 1 FROM executed WHERE safe_address=? AND safe_nonce=?",
                             (safe_address, safe_nonce)).fetchone() is not None

    def mark(self, safe_address, safe_nonce, proposal_id, tx_hash, status="OK"):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT OR REPLACE INTO executed VALUES (?,?,?,?,?,?)",
                      (safe_address, safe_nonce, proposal_id, tx_hash, status, time.time()))
