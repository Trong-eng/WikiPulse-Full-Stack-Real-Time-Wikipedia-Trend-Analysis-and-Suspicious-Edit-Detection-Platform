"""Kiểm thử broker outage chỉ trên Compose project W3 được chỉ định rõ."""

import json
import os
import socket
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic

from ingestion.collector.app.collector import Collector, run_collector
from ingestion.collector.tests.isolation import verify_broker

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("WIKIPULSE_OUTAGE_PROJECT"), reason="chưa chọn project test W3")
def test_kafka_outage_and_recovery_preserves_confirmed_prefix(monkeypatch):
    project = os.environ["WIKIPULSE_OUTAGE_PROJECT"]
    if not project.startswith("wikipulse-thanh-w3-"):
        pytest.fail("refuse non-isolated project")
    container = f"{project}-kafka-1"
    actual = subprocess.run(["docker", "inspect", "--format",
                             '{{index .Config.Labels "com.docker.compose.project"}}', container],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert actual == project
    broker = os.environ["WIKIPULSE_TEST_KAFKA"]
    verify_broker(project, broker)
    resolver = socket.getaddrinfo

    def ipv4(host, port, family=0, *args, **kwargs):
        return resolver(host, port, socket.AF_INET if host == "localhost" else family, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", ipv4)
    admin = KafkaAdminClient(bootstrap_servers=broker)
    topic = "wikipulse-w3-" + uuid.uuid4().hex
    admin.create_topics([NewTopic(topic, 1, 1)])
    gates = [threading.Event() for _ in range(4)]
    gates[0].set()
    stop = threading.Event()
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            cursor = self.headers.get("Last-Event-ID")
            start = int(cursor[1:]) if cursor else 0
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.end_headers()
            try:
                for index in range(start, 4):
                    while not gates[index].wait(0.1):
                        if stop.is_set():
                            return
                    payload = {"meta": {"id": f"event-{index + 1}"}, "wiki": "enwiki",
                               "title": "Synthetic page", "timestamp": 1767225600 + index}
                    self.wfile.write(f"id: c{index + 1}\ndata: {json.dumps(payload)}\n\n".encode())
                    self.wfile.write((":" + "x" * 600 + "\n").encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    def wait_until(predicate, label, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.2)
        pytest.fail(f"timeout: {label}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    producer = KafkaProducer(bootstrap_servers=broker, acks="all", retries=5, max_block_ms=1000)
    consumer = KafkaConsumer(topic, bootstrap_servers=broker, auto_offset_reset="earliest",
                             consumer_timeout_ms=1000, group_id=None)
    collector = Collector(producer, topic)
    session = requests.Session()

    def run():
        try:
            run_collector(collector, session, f"http://127.0.0.1:{server.server_port}", stop)
        except Exception as exc:
            errors.append(type(exc).__name__)

    runner = threading.Thread(target=run, daemon=True)
    runner.start()
    try:
        wait_until(lambda: collector.acks.cursor == "c1", "first ACK")
        subprocess.run(["docker", "stop", "-t", "10", container], check=True, capture_output=True)
        gates[1].set()
        gates[2].set()
        wait_until(lambda: {"c2", "c3"} <= {entry[0] for entry in list(collector.acks.pending)},
                   "two pending events during outage", timeout=20)
        assert collector.acks.cursor == "c1"
        subprocess.run(["docker", "start", container], check=True, capture_output=True)
        wait_until(lambda: collector.acks.cursor == "c3", "recovered ACK")
        gates[3].set()
        wait_until(lambda: collector.acks.cursor == "c4", "post-recovery ACK")
        stop.set()
        runner.join(timeout=10)
        assert not runner.is_alive()
        producer.flush(timeout=30)
        records = []
        for batch in consumer.poll(timeout_ms=1000).values():
            records.extend(json.loads(item.value)["meta"]["id"] for item in batch)
        assignment = consumer.assignment()
        assert assignment
        target = consumer.end_offsets(assignment)

        def read_complete():
            for batch in consumer.poll(timeout_ms=500).values():
                records.extend(json.loads(item.value)["meta"]["id"] for item in batch)
            return all(consumer.position(part) >= offset for part, offset in target.items())

        wait_until(read_complete, "Kafka records")
        assert not errors
        assert set(records) == {"event-1", "event-2", "event-3", "event-4"}
        print(f"OUTAGE unique={len(set(records))} records={len(records)} duplicates={len(records)-4}")
    finally:
        stop.set()
        for gate in gates:
            gate.set()
        state = subprocess.run(["docker", "inspect", "--format", "{{.State.Running}}", container],
                               capture_output=True, text=True, check=True).stdout.strip()
        if state != "true":
            subprocess.run(["docker", "start", container], check=True, capture_output=True)
        runner.join(timeout=10)
        server.shutdown()
        server.server_close()
        session.close()
        producer.close(timeout=5)
        consumer.close()
        admin.close()
        cleanup = KafkaAdminClient(bootstrap_servers=broker)
        try:
            cleanup.delete_topics([topic])
        finally:
            cleanup.close()
