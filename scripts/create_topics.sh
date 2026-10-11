#!/usr/bin/env bash
set -euo pipefail
bootstrap="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
for topic in "${KAFKA_RAW_TOPIC:-wikipedia.recentchange.raw}" "${KAFKA_DLQ_TOPIC:-wikipedia.recentchange.dlq}" wikipedia.pipeline.alerts; do
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$bootstrap" --create --if-not-exists \
    --topic "$topic" --partitions 3 --replication-factor 1
done
