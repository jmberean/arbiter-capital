import sqlite3
import json

conn = sqlite3.connect('axl_network.db')
rows = conn.execute("SELECT payload FROM messages WHERE topic='ATTACK_REJECTED'").fetchall()

for r in rows:
    print(json.dumps(json.loads(r[0]), indent=2))
