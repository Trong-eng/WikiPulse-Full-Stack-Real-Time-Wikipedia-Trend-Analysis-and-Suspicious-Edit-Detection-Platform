"""Collector với HTTP SSE cục bộ và Kafka cô lập (không dùng dữ liệu LIVE)."""

import json
import os
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic

from ingestion.collector.app.collector import Collector, run_collector

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("WIKIPULSE_TEST_KAFKA"), reason="Kafka cô lập chưa cấu hình")
def test_real_kafka_reconnect_preserves_acknowledged_cursor(monkeypatch):
    broker = os.environ["WIKIPULSE_TEST_KAFKA"]
    original_resolve = socket.getaddrinfo

    def resolve(host, port, family=0, *args, **kwargs):
        if host == "localhost":
            family = socket.AF_INET
        return original_resolve(host, port, family, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    topic = "wikipulse-test-" + uuid.uuid4().hex
    admin = KafkaAdminClient(bootstrap_servers=broker)
    admin.create_topics([NewTopic(topic, 1, 1)])
    seen_headers = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen_headers.append(self.headers.get("Last-Event-ID"))
            number = len(seen_headers)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.end_headers()
            event = {"wiki": "enwiki", "title": "Synthetic", "meta": {"id": str(number)}}
            self.wfile.write(f"id: cursor{number}\ndata: {json.dumps(event)}\n\n".encode())

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    producer = KafkaProducer(bootstrap_servers=broker, acks="all", max_block_ms=1000)
    consumer = KafkaConsumer(topic, bootstrap_servers=broker, auto_offset_reset="earliest",
                             consumer_timeout_ms=1000, group_id=None)
    collector = Collector(producer, topic)
    stop = threading.Event()
    session = requests.Session()
    runner = threading.Thread(target=run_collector,
                              args=(collector, session, f"http://127.0.0.1:{server.server_port}",
                                    stop), daemon=True)
    runner.start()
    try:
        records = []
        deadline = time.monotonic() + 20
        while len(records) < 2 and time.monotonic() < deadline:
            for batch in consumer.poll(timeout_ms=500).values():
                records.extend(json.loads(message.value) for message in batch)
        assert [row["meta"]["id"] for row in records[:2]] == ["1", "2"]
        assert seen_headers[:2] == [None, "cursor1"]
        assert all(row["collector_version"].startswith("live-") for row in records[:2])
    finally:
        stop.set()
        runner.join(timeout=5)
        server.shutdown()
        server.server_close()
        session.close()
        producer.close(timeout=5)
        consumer.close()
        admin.delete_topics([topic])
        admin.close()
