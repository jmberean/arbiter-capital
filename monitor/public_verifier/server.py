"""
Local dev server for the Arbiter Capital public audit-chain verifier.

Serves index.html and provides a JSON API that reads from the local
0g_storage/ directory and state/audit_chain_head.json.

Usage:
    python monitor/public_verifier/server.py [--port 7777]

Deploy to Vercel:
    Copy this directory; replace the /api/* routes with Vercel serverless
    functions that read from a public 0G RPC endpoint instead of local files.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE = ROOT / "0g_storage"
STATE   = ROOT / "state" / "audit_chain_head.json"
HTML    = Path(__file__).parent / "index.html"
VERIFIER = Path(__file__).parent / "verifier.html"
DB_PATH = ROOT / "axl_network.db"

PORT_DEFAULT = 7777

class VerifierHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence access log

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # ── / → index.html (Dashboard) ───────────────────────────────────
        if path in ("/", "/index.html"):
            if HTML.exists():
                self._send_html(HTML.read_bytes())
            else:
                self._send_json({"error": "index.html not found"}, 404)
            return

        # ── /verifier → verifier.html ────────────────────────────────────
        if path == "/verifier":
            if VERIFIER.exists():
                self._send_html(VERIFIER.read_bytes())
            else:
                self._send_json({"error": "verifier.html not found"}, 404)
            return

        # ── /api/head → current audit chain head ─────────────────────────
        if path == "/api/head":
            if STATE.exists():
                try:
                    data = json.loads(STATE.read_text())
                    self._send_json({"head": data.get("head")})
                except:
                    self._send_json({"head": None})
            else:
                self._send_json({"head": None})
            return

        # ── /api/dashboard → aggregated live state ──────────────────────
        if path == "/api/dashboard":
            self._handle_dashboard_api()
            return

        # ── /api/receipt/<hash> → receipt JSON ───────────────────────────
        if path.startswith("/api/receipt/"):
            tx_hash = urllib.parse.unquote(path[len("/api/receipt/"):])
            local = STORAGE / f"{tx_hash}.json"
            if local.exists():
                self._send_json(json.loads(local.read_text()))
                return
            # Scan for partial match (first 8 hex chars used as dev ID)
            if STORAGE.exists():
                for f in STORAGE.glob("*.json"):
                    if f.stem.startswith(tx_hash[:8]):
                        self._send_json(json.loads(f.read_text()))
                        return
            self._send_json({"error": f"receipt {tx_hash} not found"}, 404)
            return

        # ── /api/receipts → list all local receipts ───────────────────────
        if path == "/api/receipts":
            receipts = []
            if STORAGE.exists():
                # Sort by mtime descending
                files = sorted(STORAGE.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[:20]: # Limit to last 20
                    try:
                        d = json.loads(f.read_text())
                        receipts.append({"id": f.stem, "type": d.get("receipt_type"), "ts": d.get("timestamp")})
                    except Exception:
                        pass
            self._send_json({"receipts": receipts, "count": len(receipts)})
            return

        self._send_json({"error": "not found"}, 404)

    def _handle_dashboard_api(self):
        if not DB_PATH.exists():
            self._send_json({"error": "DB not found"}, 500)
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                
                # 1. Latest Heartbeats for Node Status
                nodes = {}
                cursor = conn.execute(
                    "SELECT sender, payload, MAX(timestamp) as ts FROM messages WHERE topic='HEARTBEAT' GROUP BY sender"
                )
                now = time.time()
                for row in cursor:
                    try:
                        payload = json.loads(row["payload"])
                        nodes[row["sender"]] = {
                            "node_id": row["sender"],
                            "last_seen": row["ts"],
                            "alive": (now - row["ts"]) < 20,
                            "status": payload.get("status", "unknown")
                        }
                    except: continue

                # 2. Latest Feed (Last 100 UNIQUE messages)
                feed = []
                cursor = conn.execute(
                    "SELECT MIN(id) as id, topic, sender, timestamp, payload "
                    "FROM messages "
                    "WHERE topic != 'HEARTBEAT' "
                    "GROUP BY topic, payload "
                    "ORDER BY id DESC LIMIT 100"
                )
                for row in cursor:
                    try:
                        feed.append({
                            "id": row["id"],
                            "topic": row["topic"],
                            "sender": row["sender"],
                            "timestamp": row["timestamp"],
                            "payload": json.loads(row["payload"])
                        })
                    except: continue

                # 3. Negotiations Discovery
                # Get all unique proposal IDs from the last 2000 messages
                negotiations = {}
                cursor = conn.execute(
                    "SELECT topic, payload FROM messages "
                    "WHERE topic IN ('PROPOSALS', 'CONSENSUS_SIGNATURES', 'PROPOSAL_EVALUATIONS', 'EXECUTION_SUCCESS', 'ATTACK_REJECTED') "
                    "ORDER BY id DESC LIMIT 2000"
                )
                
                # Temporary storage to aggregate data per pid
                pid_data = {}
                
                for row in cursor:
                    try:
                        topic = row["topic"]
                        p = json.loads(row["payload"])
                        # Proposal ID can be top-level or inside evidence for AttackRejection
                        pid = p.get("proposal_id") or p.get("evidence", {}).get("proposal_id")
                        
                        if not pid: continue
                        
                        if pid not in pid_data:
                            pid_data[pid] = {"pid": pid, "sigs": set(), "status": "negotiating", "ts": 0}
                        
                        if topic == "CONSENSUS_SIGNATURES":
                            pid_data[pid]["sigs"].add(row.get("sender") or p.get("signer_id"))
                        elif topic == "EXECUTION_SUCCESS":
                            pid_data[pid]["status"] = "executed"
                        elif topic == "ATTACK_REJECTED":
                            pid_data[pid]["status"] = "attack_blocked"
                        elif topic == "PROPOSAL_EVALUATIONS" and pid_data[pid]["status"] == "negotiating":
                            if p.get("consensus_status") == "REJECTED":
                                pid_data[pid]["status"] = "rejected"
                    except: continue

                # Format for frontend
                for pid, info in pid_data.items():
                    # Filter out adversary attacks from the main list if they are too numerous, 
                    # but keep them if they are recent.
                    # For now, just show everything but prioritize real ones.
                    negotiations[pid] = {
                        "proposal_id": pid,
                        "signatures": len(info["sigs"]),
                        "status": info["status"]
                    }

                neg_list = list(negotiations.values())
                # Sort: Executed first, then by ID descending
                neg_list.sort(key=lambda x: (x["status"] == "negotiating", x["proposal_id"]), reverse=True)

                self._send_json({
                    "nodes": list(nodes.values()),
                    "feed": feed,
                    "negotiations": neg_list[:15], # Top 15
                    "server_time": now,
                    "safe_address": os.getenv("SAFE_ADDRESS", "0x...")
                })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)



def main():
    parser = argparse.ArgumentParser(description="Arbiter Capital public verifier server")
    parser.add_argument("--port", type=int, default=PORT_DEFAULT, help=f"Port (default {PORT_DEFAULT})")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), VerifierHandler)
    url = f"http://localhost:{args.port}"
    print(f"Arbiter Capital Public Verifier")
    print(f"  Serving: {url}")
    print(f"  Storage: {STORAGE}")
    print(f"  Chain head: {STATE}")
    print(f"\nOpen {url} in a browser, or scan the QR in the God View monitor.")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
