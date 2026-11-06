#!/usr/bin/env bash
set -euo pipefail

# A successful RPC alone does not prove a registered DataNode can store a block.
registered=false
for attempt in {1..30}; do
  if hdfs dfsadmin -report -live 2>/dev/null | grep -q 'Live datanodes (1)'; then
    registered=true
    break
  fi
  sleep 2
done
if [[ "$registered" != true ]]; then
  echo 'No registered DataNode after bounded readiness wait' >&2
  exit 1
fi
hdfs dfs -mkdir -p /wikipulse /checkpoints
probe="/wikipulse/.readiness-$(date +%s)-$$"
trap 'hdfs dfs -rm -f "$probe" >/dev/null 2>&1 || true' EXIT
printf 'wikipulse-ready' | hdfs dfs -put - "$probe"
[[ "$(hdfs dfs -cat "$probe")" == 'wikipulse-ready' ]]
echo 'HDFS_READINESS=passed (write/read)'
