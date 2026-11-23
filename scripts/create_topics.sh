#!/usr/bin/env bash
set -euo pipefail
bootstrap="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
raw="${KAFKA_RAW_TOPIC:-wikipedia.recentchange.raw}"
retention="${KAFKA_RAW_RETENTION_MS:-86400000}"
if [[ ! "$retention" =~ ^[1-9][0-9]*$ ]]; then
  echo 'KAFKA_RAW_RETENTION_MS must be a positive integer' >&2
  exit 2
fi
# --if-not-exists preserves retention on existing topics.
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$bootstrap" --create --if-not-exists \
  --topic "$raw" --partitions 3 --replication-factor 1 --config "retention.ms=$retention"

for topic in "${KAFKA_DLQ_TOPIC:-wikipedia.recentchange.dlq}" wikipedia.pipeline.alerts; do
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$bootstrap" --create --if-not-exists \
    --topic "$topic" --partitions 3 --replication-factor 1
done
