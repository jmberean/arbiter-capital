#!/usr/bin/env bash
# Start 5 separate axl-node instances (one per daemon) on distinct ports.
# Each node connects to the live Gensyn public peers and gets its own
# IPv6 identity on the Yggdrasil mesh.
#
# Run once before `python scripts/start_all.py`.
# Stop with: pkill -f axl-node

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

mkdir -p state/axl state/axl_logs

PROCESSES=(quant patriarch exec keeperhub watchdog)
API_PORTS=(9011   9012      9013  9014       9015)
# All nodes share tcp_port=7000 — each has its own gVisor stack/IPv6 so no collision.
# The dial code always connects to destination_ipv6:sender_tcp_port, so all must match.
TCP_PORTS=(7000   7000      7000  7000       7000)

PUBLIC_PEERS='["tls://34.46.48.224:9001","tls://136.111.135.206:9001"]'
# quant node acts as a local hub (Listen on 9021) so all 5 nodes can route to each other
# without relying solely on public-node relay paths.
HUB_PEER="tls://127.0.0.1:9021"

for i in "${!PROCESSES[@]}"; do
  name="${PROCESSES[$i]}"
  api_port="${API_PORTS[$i]}"
  tcp_port="${TCP_PORTS[$i]}"
  pem="state/axl/${name}.pem"
  cfg="state/axl/${name}-config.json"

  if [ ! -f "$pem" ]; then
    openssl genpkey -algorithm ed25519 -out "$pem"
    echo "[axl] Generated key: $pem"
  fi

  if [ "$name" = "quant" ]; then
    # Hub node: listens for inbound local connections
    cat > "$cfg" <<EOF
{
  "PrivateKeyPath": "${pem}",
  "Peers": ${PUBLIC_PEERS},
  "Listen": ["${HUB_PEER}"],
  "api_port": ${api_port},
  "tcp_port": ${tcp_port}
}
EOF
  else
    # Spoke nodes: peer to local hub + public peers
    cat > "$cfg" <<EOF
{
  "PrivateKeyPath": "${pem}",
  "Peers": ["${HUB_PEER}", "tls://34.46.48.224:9001", "tls://136.111.135.206:9001"],
  "Listen": [],
  "api_port": ${api_port},
  "tcp_port": ${tcp_port}
}
EOF
  fi

  log="state/axl_logs/${name}.log"
  axl-node -config "$cfg" > "$log" 2>&1 &
  echo "[axl] Started ${name} node — api=:${api_port} tcp=:${tcp_port} (pid $!, log: ${log})"
done

echo ""
echo "[axl] All 5 nodes started. Waiting 3s for peer connections..."
sleep 3

for i in "${!PROCESSES[@]}"; do
  name="${PROCESSES[$i]}"
  api_port="${API_PORTS[$i]}"
  status=$(curl -sf "http://127.0.0.1:${api_port}/topology" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"ok — {len(d['peers'])} peers, pubkey={d['our_public_key'][:12]}...\")" 2>/dev/null || echo "UNREACHABLE")
  echo "[axl] ${name} (${api_port}): ${status}"
done

echo ""
echo "[axl] Capturing node public keys..."
PUBKEYS=""
for i in "${!PROCESSES[@]}"; do
  name="${PROCESSES[$i]}"
  api_port="${API_PORTS[$i]}"
  pubkey=$(curl -sf "http://127.0.0.1:${api_port}/topology" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['our_public_key'])" 2>/dev/null || echo "")
  if [ -n "$pubkey" ]; then
    echo "[axl] ${name} pubkey: ${pubkey}"
    PUBKEYS="${PUBKEYS}${pubkey},"
  fi
done
PUBKEYS="${PUBKEYS%,}"

# Update AXL_PEER_KEYS in .env
if [ -n "$PUBKEYS" ]; then
  if grep -q "^AXL_PEER_KEYS=" "$ROOT/.env" 2>/dev/null; then
    sed -i.bak "s|^AXL_PEER_KEYS=.*|AXL_PEER_KEYS=${PUBKEYS}|" "$ROOT/.env" && rm -f "$ROOT/.env.bak"
  else
    printf "\nAXL_PEER_KEYS=${PUBKEYS}\n" >> "$ROOT/.env"
  fi
  echo "[axl] AXL_PEER_KEYS written to .env"
fi
