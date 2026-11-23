"""Thành phần collector LIVE và theo dõi xác nhận Kafka."""

import json
import logging
import queue
import random
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests

from ingestion.collector.app.recording import RecordingError
from ingestion.collector.app.sse import parse_sse
from ingestion.envelope import encode_event

logger = logging.getLogger(__name__)


class PublishFailure(Exception):
    """Kafka không xác nhận một hoặc nhiều sự kiện."""


class PermanentStreamError(Exception):
    """Nguồn từ chối request hoặc cấu hình sai, không retry vô hạn."""


class AckTracker:
    """Chỉ tiến cursor qua tiền tố liên tiếp đã được broker xác nhận."""

    def __init__(self):
        self.cursor = None
        self.pending = deque()
        self.published = 0
        self.failed = False

    def add(self, event_id, future, on_ack=None):
        self.pending.append((event_id, future, on_ack))

    def poll(self):
        if self.failed:
            raise PublishFailure("Kafka publish failed")
        completed = 0
        while self.pending and self.pending[0][1].is_done:
            event_id, future, on_ack = self.pending[0]
            if future.exception is not None:
                self.failed = True
                raise PublishFailure("Kafka publish failed")
            if on_ack is not None:
                try:
                    on_ack()
                except RecordingError:
                    self.failed = True
                    raise
            self.pending.popleft()
            if event_id is not None:
                self.cursor = event_id
            self.published += 1
            completed += 1
        return completed


def prepare_event(line):
    """Dùng envelope hiện có và báo riêng JSON không phải object/không hợp lệ."""
    try:
        malformed = not isinstance(json.loads(line), dict)
    except (ValueError, TypeError):
        malformed = True
    key, payload = encode_event(line, datetime.now(timezone.utc), source="live")
    return key, payload, malformed


@dataclass
class Counters:
    received: int = 0
    published: int = 0
    publish_failed: int = 0
    parse_errors: int = 0
    reconnects: int = 0
    last_event_time: str | None = None


class Collector:
    def __init__(self, producer, topic, recorder=None):
        self.producer = producer
        self.topic = topic
        self.acks = AckTracker()
        self.counters = Counters()
        self.recorder = recorder

    def publish(self, event):
        self.counters.received += 1
        key, payload, malformed = prepare_event(event.data)
        self.counters.parse_errors += int(malformed)
        if not malformed:
            document = json.loads(event.data)
            meta = document.get("meta")
            if isinstance(meta, dict) and isinstance(meta.get("dt"), str):
                try:
                    timestamp = datetime.fromisoformat(meta["dt"].replace("Z", "+00:00"))
                    if timestamp.tzinfo is not None:
                        self.counters.last_event_time = timestamp.astimezone(timezone.utc).isoformat()
                except (ValueError, OverflowError):
                    pass
        record = self.recorder.prepare(event.data) if self.recorder is not None else None
        try:
            future = self.producer.send(self.topic, key=key, value=payload)
        except Exception as exc:
            self.counters.publish_failed += 1
            raise PublishFailure("Kafka send failed") from exc
        self.acks.add(event.id, future,
                      (lambda: self.recorder.write(record)) if self.recorder is not None else None)

    def poll(self):
        try:
            self.acks.poll()
        except PublishFailure:
            self.counters.publish_failed += 1
            raise
        finally:
            self.counters.published = self.acks.published

    def log_counters(self):
        logger.info("counters %s", json.dumps(asdict(self.counters), sort_keys=True))


def consume_connection(response, collector, stop):
    """Đọc stream trên thread riêng để poll ACK và shutdown ngay cả khi SSE im lặng."""
    events = queue.Queue(maxsize=100)
    reader_stop = threading.Event()
    ended = object()

    def put(item):
        while not reader_stop.is_set():
            try:
                events.put(item, timeout=0.2)
                return
            except queue.Full:
                continue

    def read():
        try:
            for event in parse_sse(response.iter_lines(decode_unicode=True),
                                   initial_id=collector.acks.cursor):
                if reader_stop.is_set():
                    break
                put(event)
        except Exception:
            pass  # Lỗi transport không được đưa raw exception vào log.
        finally:
            put(ended)

    thread = threading.Thread(target=read, daemon=True, name="sse-reader")
    thread.start()
    finished = False
    pending_since = None
    previous_head = None
    try:
        while True:
            collector.poll()
            now = time.monotonic()
            if collector.acks.pending:
                head = collector.acks.pending[0][1]
                if head is not previous_head:
                    pending_since = now
                    previous_head = head
                elif now - pending_since >= 30:
                    collector.counters.publish_failed += 1
                    raise PublishFailure("Kafka acknowledgement timed out")
            else:
                pending_since = None
                previous_head = None
            if (finished or stop.is_set()) and not collector.acks.pending:
                break
            if stop.is_set() or finished or len(collector.acks.pending) >= 100:
                time.sleep(0.05)
                continue
            try:
                event = events.get(timeout=1)
            except queue.Empty:
                continue
            if event is ended:
                finished = True
            else:
                collector.publish(event)
    finally:
        reader_stop.set()


def report_counters(collector, stopped):
    while not stopped.wait(30):
        collector.log_counters()


def run_collector(collector, session, url, stop, *, wait=None):
    """Kết nối lại trong cùng tiến trình, resume từ prefix ACK an toàn."""
    reporter_stop = threading.Event()
    reporter = threading.Thread(target=report_counters, args=(collector, reporter_stop),
                                daemon=True, name="collector-counters")
    reporter.start()
    try:
        _run_collector(collector, session, url, stop, wait=wait)
    finally:
        reporter_stop.set()
        reporter.join(timeout=1)


def _run_collector(collector, session, url, stop, *, wait=None):
    wait = wait or stop.wait
    delay = 1
    while not stop.is_set():
        response = None
        published_before = collector.counters.published
        headers = {
            "Accept": "text/event-stream",
            "User-Agent": "WikiPulse/0.1 (https://github.com/Trong-eng/"
                          "WikiPulse-Full-Stack-Real-Time-Wikipedia-Trend-Analysis-and-Suspicious-Edit-Detection-Platform)",
        }
        if collector.acks.cursor:
            headers["Last-Event-ID"] = collector.acks.cursor
        try:
            response = session.get(url, headers=headers, stream=True, timeout=(10, 60))
            if 400 <= response.status_code < 500 and response.status_code not in (408, 429):
                raise PermanentStreamError(f"SSE HTTP {response.status_code}")
            if response.status_code != 200:
                raise ConnectionError("SSE unavailable")
            response.encoding = "utf-8"
            consume_connection(response, collector, stop)
        except PermanentStreamError:
            raise
        except RecordingError:
            raise
        except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema,
                requests.exceptions.MissingSchema):
            raise PermanentStreamError("Invalid stream URL") from None
        except Exception as exc:
            if isinstance(exc, PublishFailure):
                if stop.is_set():
                    raise
                collector.acks.pending.clear()
                collector.acks.failed = False
            logger.warning("collector_connection_failed type=%s", type(exc).__name__)
        finally:
            if response is not None:
                # requests.close() can wait for a reader blocked in iter_lines().
                threading.Thread(target=response.close, daemon=True).start()
        if stop.is_set():
            break
        collector.counters.reconnects += 1
        if collector.counters.published > published_before:
            delay = 1
        wait(min(60, delay + random.uniform(0, 0.25)))
        delay = min(60, delay * 2)
