import sqlite3
import json

conn = sqlite3.connect('axl_network.db')
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM messages WHERE topic='PROPOSALS' ORDER BY id DESC LIMIT 1").fetchone()

if row:
    d = dict(row)
    # The payload is likely a JSON string in the DB, let's parse it if so
    try:
        d['payload'] = json.loads(d['payload'])
    except:
        pass
    print(json.dumps(d, indent=2))
else:
    print("No proposals found.")
