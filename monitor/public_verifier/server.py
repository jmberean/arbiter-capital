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
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE = ROOT / "0g_storage"
STATE   = ROOT / "state" / "audit_chain_head.json"
HTML    = Path(__file__).parent / "index.html"

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

        # ── / → index.html ───────────────────────────────────────────────
        if path in ("/", "/index.html"):
            if HTML.exists():
                self._send_html(HTML.read_bytes())
            else:
                self._send_json({"error": "index.html not found"}, 404)
            return

        # ── /api/head → current audit chain head ─────────────────────────
        if path == "/api/head":
            if STATE.exists():
                data = json.loads(STATE.read_text())
                self._send_json({"head": data.get("head")})
            else:
                self._send_json({"head": None})
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
                for f in sorted(STORAGE.glob("*.json"), key=lambda p: p.stat().st_mtime):
                    try:
                        d = json.loads(f.read_text())
                        receipts.append({"id": f.stem, "type": d.get("receipt_type"), "ts": d.get("timestamp")})
                    except Exception:
                        pass
            self._send_json({"receipts": receipts, "count": len(receipts)})
            return

        self._send_json({"error": "not found"}, 404)


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
