import sqlite3
import json

conn = sqlite3.connect('axl_network.db')
row = conn.execute("SELECT payload FROM messages WHERE topic='PROPOSAL_EVALUATIONS' ORDER BY id DESC LIMIT 1").fetchone()

if row:
    print(json.dumps(json.loads(row[0]), indent=2))
else:
    print("No evaluations found.")
