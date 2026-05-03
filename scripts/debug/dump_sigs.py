import sqlite3
import json

conn = sqlite3.connect('axl_network.db')
rows = conn.execute("SELECT sender, payload FROM messages WHERE topic='CONSENSUS_SIGNATURES'").fetchall()

for s, p in rows:
    p_json = json.loads(p)
    print(f"Sender: {s} | Proposal: {p_json['proposal_id']} | Iteration: {p_json['iteration']}")
