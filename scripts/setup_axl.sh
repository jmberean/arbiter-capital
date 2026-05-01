#!/usr/bin/env bash
# Updated for live Gensyn AXL config format (JSON)

set -euo pipefail
PORTS=(9001 9002 9003 9004 9005)
NODE_IDS=("Quant_Node_A" "Patriarch_Node_B" "Execution_Node_P3" "KeeperHub_Sim_P4" "Adversary_Node_Z")

mkdir -p state/axl_logs
mkdir -p state/axl_configs

# Node 1 is our hub for this local mesh
HUB_PEER="tls://127.0.0.1:9001"

for i in "${!PORTS[@]}"; do
  CONFIG_FILE="state/axl_configs/${NODE_IDS[$i]}.json"
  
  # Set peers (Hub connects to no one initially, everyone else connects to the Hub)
  if [ $i -eq 0 ]; then
    PEERS="[]"
  else
    PEERS="[\"$HUB_PEER\"]"
  fi

  # Generate the JSON config
  cat <<EOF > "$CONFIG_FILE"
{
  "PrivateKeyPath": "state/axl_keys/${NODE_IDS[$i]}.pem",
  "Listen": ["tls://127.0.0.1:${PORTS[$i]}"],
  "Peers": $PEERS
}
EOF

  # Launch the node
  ./axl-node.exe -config "$CONFIG_FILE" > "state/axl_logs/${NODE_IDS[$i]}.log" 2>&1 &
  echo "Started ${NODE_IDS[$i]} on port ${PORTS[$i]} (pid $!)"
done

wait