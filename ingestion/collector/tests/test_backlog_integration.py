"""Đo thời gian ba Spark Kafka queries bắt kịp offsets tổng hợp trong project cô lập."""

import json
import os
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone

import pytest
from kafka import KafkaConsumer, KafkaProducer

from ingestion.collector.tests.isolation import verify_broker

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("WIKIPULSE_CATCHUP_PROJECT"), reason="chưa chọn project Spark W3")
def test_spark_kafka_queries_catch_up_synthetic_backlog(monkeypatch):
    project = os.environ["WIKIPULSE_CATCHUP_PROJECT"]
    if not project.startswith("wikipulse-thanh-w3-"):
        pytest.fail("refuse non-isolated project")
    container = f"{project}-spark-1"
    label = subprocess.run(["docker", "inspect", "--format",
                            '{{index .Config.Labels "com.docker.compose.project"}}', container],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert label == project
    broker = os.environ["WIKIPULSE_TEST_KAFKA"]
    verify_broker(project, broker)
    resolver = socket.getaddrinfo

    def ipv4(host, port, family=0, *args, **kwargs):
        return resolver(host, port, socket.AF_INET if host == "localhost" else family, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", ipv4)
    topic = "wikipedia.recentchange.raw"
    consumer = KafkaConsumer(bootstrap_servers=broker, group_id=None)
    partitions = consumer.partitions_for_topic(topic)
    assert partitions
    from kafka import TopicPartition

    assigned = [TopicPartition(topic, partition) for partition in partitions]
    producer = KafkaProducer(bootstrap_servers=broker, acks="all")
    try:
        start_offsets = {str(part.partition): offset for part, offset in consumer.end_offsets(assigned).items()}
        assert all(offset == 0 for offset in start_offsets.values()), "use a fresh isolated project"
        subprocess.run(["docker", "stop", "-t", "100", container], check=True, capture_output=True)
        run_id = uuid.uuid4().hex
        futures = []
        for index in range(1200):
            event = {"meta": {"id": f"synthetic-{run_id}-{index}", "domain": "en.wikipedia.org"},
                     "wiki": "enwiki", "title": "Synthetic page", "type": "edit",
                     "timestamp": 1767225600 + index % 30, "user": "SyntheticEditor"}
            futures.append(producer.send(topic, key=b"enwiki:Synthetic page", value=json.dumps(event).encode()))
        for future in futures:
            future.get(timeout=60)
        producer.flush(timeout=60)
        started = time.monotonic()
        started_utc = datetime.now(timezone.utc)
        target = {str(part.partition): offset for part, offset in consumer.end_offsets(assigned).items()}
        assert sum(target[key] - start_offsets[key] for key in target) == 1200
        subprocess.run(["docker", "start", container], check=True, capture_output=True)
        deadline = time.monotonic() + 300
        achieved = {}
        while time.monotonic() < deadline:
            result = subprocess.run(["docker", "exec", container, "python", "-c",
                                     "import json; print(open('/data/progress.json').read())"],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                snapshot = json.loads(result.stdout)
                updated = datetime.fromisoformat(snapshot["updated_at"].replace("Z", "+00:00"))
                if updated < started_utc:
                    time.sleep(2)
                    continue
                progress = snapshot["queries"]
                for name in ("bronze_raw", "bronze_invalid", "silver_events"):
                    if not snapshot["active_queries"].get(name):
                        continue
                    data = progress.get(name) or {}
                    for source in data.get("sources", []):
                        offsets = source.get("endOffset", {})
                        if isinstance(offsets, str):
                            offsets = json.loads(offsets)
                        actual = offsets.get(topic, {})
                        if all(int(actual.get(part, -1)) >= end for part, end in target.items()):
                            achieved.setdefault(name, round(time.monotonic() - started, 3))
                if len(achieved) == 3:
                    break
            time.sleep(2)
        assert len(achieved) == 3, f"query offsets not reached: {achieved} target={target}"
        print(f"CATCHUP events=1200 seconds={max(achieved.values())} queries={achieved} "
              f"start={start_offsets} target={target}")
    finally:
        state = subprocess.run(["docker", "inspect", "--format", "{{.State.Running}}", container],
                               capture_output=True, text=True).stdout.strip()
        if state == "false":
            subprocess.run(["docker", "start", container], capture_output=True)
        producer.close(timeout=5)
        consumer.close()
