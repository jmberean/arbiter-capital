#!/usr/bin/env bash
# scripts/setup_axl.sh — bring up 5 distinct AXL nodes locally for demo path
# Per Gensyn AXL docs:

set -euo pipefail
PORTS=(9001 9002 9003 9004 9005)
NODE_IDS=("Quant_Node_A" "Patriarch_Node_B" "Execution_Node_P3" "KeeperHub_Sim_P4" "Adversary_Node_Z")

mkdir -p ./state/axl_keys
mkdir -p ./state/axl_logs

for i in "${!PORTS[@]}"; do
  # The exact AXL CLI flags must be verified against the live Gensyn docs
  # This is a representative scaffold based on the roadmap
  axl-node \
    --listen "127.0.0.1:${PORTS[$i]}" \
    --node-id "${NODE_IDS[$i]}" \
    --keystore "./state/axl_keys/${NODE_IDS[$i]}.key" \
    --peers "127.0.0.1:9001,127.0.0.1:9002,127.0.0.1:9003,127.0.0.1:9004,127.0.0.1:9005" \
    --log-file "./state/axl_logs/${NODE_IDS[$i]}.log" &
  echo "Started ${NODE_IDS[$i]} on port ${PORTS[$i]} (pid $!)"
done
wait
