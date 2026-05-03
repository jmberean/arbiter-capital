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
                now = time.time()

                # 1. Node status from heartbeats — use `role` field, alive if seen within 60s.
                #    Use MAX(id) subquery so the payload matches the latest row (SQLite GROUP BY
                #    does not guarantee non-aggregated columns come from the max-aggregate row).
                nodes = {}
                cursor = conn.execute(
                    "SELECT sender, payload, timestamp as ts FROM messages "
                    "WHERE topic='HEARTBEAT' AND id IN "
                    "(SELECT MAX(id) FROM messages WHERE topic='HEARTBEAT' GROUP BY sender)"
                )
                for row in cursor:
                    try:
                        p = json.loads(row["payload"])
                        nodes[row["sender"]] = {
                            "node_id": row["sender"],
                            "last_seen": row["ts"],
                            "alive": (now - row["ts"]) < 60,
                            "status": p.get("role", p.get("status", "idle")),
                        }
                    except: continue

                # 2. Feed (last 80 unique messages) — kept for timeline modal.
                #    Use MAX(id) so we get the most recent occurrence of each unique payload;
                #    MIN(id) would give the oldest cross-run copy whose timestamp predates the
                #    current session and gets filtered out in the modal.
                feed = []
                cursor = conn.execute(
                    "SELECT MAX(id) as id, topic, sender, timestamp, payload "
                    "FROM messages WHERE topic != 'HEARTBEAT' "
                    "GROUP BY topic, payload ORDER BY id DESC LIMIT 80"
                )
                for row in cursor:
                    try:
                        feed.append({
                            "id": row["id"], "topic": row["topic"],
                            "sender": row["sender"], "timestamp": row["timestamp"],
                            "payload": json.loads(row["payload"])
                        })
                    except: continue

                # 3. Enriched negotiations — one entry per proposal_id.
                #
                # Session isolation: proposal_ids are reused across demo runs. We only want
                # events that belong to the *current* session for each pid, defined as events
                # that occurred at or after the most recent PROPOSALS message for that pid.
                # Anything older is a stale artifact from a previous run.
                #
                # Pass A: find the timestamp of the most recent PROPOSALS message per pid.
                session_start = {}
                for row in conn.execute(
                    "SELECT json_extract(payload,'$.proposal_id') as pid, MAX(timestamp) as ts "
                    "FROM messages WHERE topic='PROPOSALS' GROUP BY pid"
                ):
                    if row["pid"]:
                        session_start[row["pid"]] = row["ts"]

                # Pass B: build pid_data, skipping downstream events that predate the session.
                pid_data = {}
                cursor = conn.execute(
                    "SELECT topic, sender, timestamp, payload FROM messages "
                    "WHERE topic IN ('PROPOSALS','CONSENSUS_SIGNATURES','PROPOSAL_EVALUATIONS','EXECUTION_SUCCESS','ATTACK_REJECTED') "
                    "ORDER BY id DESC LIMIT 2000"
                )
                for row in cursor:
                    try:
                        topic = row["topic"]
                        p = json.loads(row["payload"])
                        ts = row["timestamp"]
                        pid = p.get("proposal_id") or (p.get("evidence") or {}).get("proposal_id")
                        if not pid: continue

                        # Skip events that predate the current session for this pid
                        sess = session_start.get(pid, 0)
                        if topic != "PROPOSALS" and ts < sess:
                            continue

                        if pid not in pid_data:
                            pid_data[pid] = {
                                "pid": pid, "sigs": set(), "status": "proposed",
                                "asset_in": "", "asset_out": "", "amount_in_units": "",
                                "asset_in_decimals": 18,
                                "quant_rationale": "", "guardian_rationale": "",
                                "rejection_reason": "", "tx_hash": "",
                                "first_ts": ts,
                                "last_ts": ts,  # set once on first encounter (DESC = most recent)
                            }
                        else:
                            pid_data[pid]["first_ts"] = ts  # keep overwriting to oldest

                        d = pid_data[pid]

                        if topic == "PROPOSALS":
                            if not d["asset_in"]:
                                d["asset_in"] = p.get("asset_in") or ""
                                d["asset_out"] = p.get("asset_out") or ""
                                d["amount_in_units"] = str(p.get("amount_in_units") or "")
                                d["asset_in_decimals"] = p.get("asset_in_decimals") or 18
                                d["quant_rationale"] = p.get("rationale") or ""
                        elif topic == "PROPOSAL_EVALUATIONS":
                            cs = p.get("consensus_status")
                            if cs == "REJECTED":
                                if d["status"] not in ("executed", "attack_blocked"):
                                    d["status"] = "rejected"
                                    if not d["rejection_reason"]:
                                        d["rejection_reason"] = p.get("rejection_reason") or (p.get("rationale") or "")[:100]
                            else:
                                if not d["guardian_rationale"] and cs == "ACCEPTED":
                                    d["guardian_rationale"] = p.get("rationale") or ""
                                if d["status"] == "proposed":
                                    d["status"] = "evaluated"
                        elif topic == "CONSENSUS_SIGNATURES":
                            sig_key = p.get("signer_address") or p.get("signer_id") or row["sender"]
                            d["sigs"].add(sig_key)
                            if d["status"] not in ("executed", "attack_blocked", "rejected"):
                                d["status"] = "signing"
                        elif topic == "EXECUTION_SUCCESS":
                            d["status"] = "executed"
                            d["rejection_reason"] = ""
                            if not d["tx_hash"]: d["tx_hash"] = p.get("tx_hash", "")
                        elif topic == "ATTACK_REJECTED":
                            d["status"] = "attack_blocked"
                            if not d["rejection_reason"]:
                                d["rejection_reason"] = p.get("rejection_reason", "adversarial payload")
                    except: continue

                def _is_attack(d):
                    pid = d["pid"].lower()
                    return (
                        d["status"] == "attack_blocked"
                        or pid.startswith("attack_")
                        or pid.startswith("emergency_")
                        or pid.startswith("atk_")
                    )

                THRESHOLD = 2
                all_rows = sorted(
                    [{"proposal_id": d["pid"],
                      # Cap at threshold; executed proposals always show 2/2 regardless of accumulated history
                      "signatures": THRESHOLD if d["status"] == "executed" else min(len(d["sigs"]), THRESHOLD),
                      "status": d["status"], "asset_in": d["asset_in"],
                      "asset_out": d["asset_out"], "amount_in_units": d["amount_in_units"],
                      "asset_in_decimals": d["asset_in_decimals"],
                      "quant_rationale": d["quant_rationale"],
                      "guardian_rationale": d["guardian_rationale"],
                      "rejection_reason": d["rejection_reason"],
                      "tx_hash": d["tx_hash"], "ts": d["last_ts"],
                      "session_start_ts": session_start.get(d["pid"], 0),
                      "is_attack": _is_attack(d)}
                     for d in pid_data.values()],
                    key=lambda x: -x["ts"]
                )

                legit  = [x for x in all_rows if not x["is_attack"] and x["asset_in"] and x["asset_out"]]
                attacks = [x for x in all_rows if x["is_attack"]]

                self._send_json({
                    "nodes": list(nodes.values()),
                    "feed": feed,
                    "negotiations": legit[:20],
                    "attacks": attacks[:5],        # most recent 5 attacks for the threat panel
                    "attack_count": len(attacks),
                    "server_time": now,
                    "safe_address": os.getenv("SAFE_ADDRESS", "0x...")
                })
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
