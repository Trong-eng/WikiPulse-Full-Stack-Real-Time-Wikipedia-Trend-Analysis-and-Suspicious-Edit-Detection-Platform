import json
import threading
import time

import pytest
import requests

from ingestion.collector.app.collector import (
    AckTracker,
    Collector,
    PermanentStreamError,
    PublishFailure,
    consume_connection,
    prepare_event,
    report_counters,
    run_collector,
)
from ingestion.collector.app.sse import SSEEvent


class Future:
    def __init__(self, done=False, error=None):
        self.is_done = done
        self.exception = error


def test_ack_cursor_waits_for_contiguous_success():
    tracker = AckTracker()
    first, second = Future(), Future(done=True)
    tracker.add("a", first)
    tracker.add("b", second)
    assert tracker.poll() == 0
    assert tracker.cursor is None
    first.is_done = True
    assert tracker.poll() == 2
    assert tracker.cursor == "b"


def test_failed_ack_never_advances_cursor_past_failure():
    tracker = AckTracker()
    tracker.add("a", Future(done=True))
    tracker.add("b", Future(done=True, error=RuntimeError("private data")))
    tracker.add("c", Future(done=True))
    with pytest.raises(PublishFailure):
        tracker.poll()
    assert tracker.cursor == "a"
    with pytest.raises(PublishFailure):
        tracker.poll()
    assert tracker.cursor == "a"


def test_prepare_event_stamps_live_and_reports_parse_error():
    key, payload, malformed = prepare_event('{"wiki":"enwiki","title":"A"}')
    assert key == b"enwiki:A"
    assert json.loads(payload)["collector_version"].startswith("live-")
    assert not malformed
    assert prepare_event("broken")[2]
    assert prepare_event("[]")[2]


def test_collector_sends_live_envelope_and_counts_only_after_ack():
    class Producer:
        def __init__(self):
            self.sent = []
            self.future = Future()

        def send(self, topic, *, key, value):
            self.sent.append((topic, key, value))
            return self.future

    producer = Producer()
    collector = Collector(producer, "raw")
    collector.publish(SSEEvent('{"wiki":"enwiki","title":"A"}', "id1"))
    assert collector.counters.received == 1
    assert collector.counters.published == 0
    assert producer.sent[0][0:2] == ("raw", b"enwiki:A")
    producer.future.is_done = True
    collector.poll()
    assert collector.counters.published == 1
    assert collector.acks.cursor == "id1"


def test_collector_counts_invalid_json_without_logging_payload():
    class Producer:
        def send(self, topic, *, key, value):
            assert key is None
            return Future(done=True)

    collector = Collector(Producer(), "raw")
    collector.publish(SSEEvent("bad-json", "id1"))
    collector.poll()
    assert collector.counters.parse_errors == 1
    assert collector.counters.published == 1


def test_last_event_time_ignores_non_timestamp_text():
    class Producer:
        def send(self, topic, *, key, value):
            return Future(done=True)

    collector = Collector(Producer(), "raw")
    collector.publish(SSEEvent('{"meta":{"dt":"private value"}}', "x"))
    assert collector.counters.last_event_time is None


def test_extreme_timezone_does_not_stop_collector():
    class Producer:
        def send(self, topic, *, key, value):
            return Future(done=True)

    collector = Collector(Producer(), "raw")
    collector.publish(SSEEvent('{"meta":{"dt":"9999-12-31T23:59:59-14:00"}}', "x"))
    collector.poll()
    assert collector.counters.last_event_time is None
    assert collector.counters.published == 1


def test_connection_delivers_sse_and_ack_before_eof():
    class Response:
        def iter_lines(self, **kwargs):
            return iter(['id: cursor1', 'data: {"wiki":"enwiki","title":"A"}', ''])

    class Producer:
        def send(self, topic, *, key, value):
            return Future(done=True)

    collector = Collector(Producer(), "raw")
    consume_connection(Response(), collector, threading.Event())
    assert collector.acks.cursor == "cursor1"
    assert collector.counters.published == 1


def test_reconnect_passes_only_acknowledged_cursor():
    stop = threading.Event()

    class Response:
        status_code = 200
        encoding = None

        def iter_lines(self, **kwargs):
            return iter(['id: safe', 'data: {"wiki":"enwiki","title":"A"}', ''])

        def close(self):
            pass

    class Session:
        def __init__(self):
            self.headers = []

        def get(self, url, **kwargs):
            self.headers.append(kwargs["headers"])
            if len(self.headers) == 2:
                stop.set()
            return Response()

    class Producer:
        def send(self, topic, *, key, value):
            return Future(done=True)

    session = Session()
    collector = Collector(Producer(), "raw")
    run_collector(collector, session, "https://example.invalid", stop, wait=lambda _: None)
    assert session.headers[1]["Last-Event-ID"] == "safe"
    assert collector.counters.reconnects == 1


def test_http_403_is_fatal_without_reconnect():
    class Session:
        def get(self, url, **kwargs):
            class Response:
                status_code = 403

                def close(self):
                    pass
            return Response()

    with pytest.raises(PermanentStreamError):
        run_collector(Collector(object(), "raw"), Session(), "https://example.invalid",
                      threading.Event(), wait=lambda _: None)


def test_invalid_url_is_permanent():
    stop = threading.Event()
    class Session:
        def get(self, url, **kwargs):
            raise requests.exceptions.InvalidURL("private")

    with pytest.raises(PermanentStreamError):
        run_collector(Collector(object(), "raw"), Session(), "http://", stop,
                      wait=lambda _: stop.set())


def test_http_429_retries():
    stop = threading.Event()

    class Response:
        status_code = 429

        def close(self):
            pass

    class Session:
        def get(self, url, **kwargs):
            return Response()

    collector = Collector(object(), "raw")
    run_collector(collector, Session(), "https://example.invalid", stop,
                  wait=lambda _: stop.set())
    assert collector.counters.reconnects == 1


def test_blocked_response_close_does_not_block_shutdown():
    stop = threading.Event()
    release = threading.Event()

    class Response:
        status_code = 200
        encoding = None

        def iter_lines(self, **kwargs):
            stop.set()
            release.wait(3)
            return iter(())

        def close(self):
            release.wait(3)

    class Session:
        def get(self, url, **kwargs):
            return Response()

    start = time.monotonic()
    run_collector(Collector(object(), "raw"), Session(), "https://example.invalid", stop)
    elapsed = time.monotonic() - start
    release.set()
    assert elapsed < 2


def test_publish_failure_during_shutdown_is_reported(monkeypatch):
    from ingestion.collector.app import collector as collector_module

    stop = threading.Event()

    class Response:
        status_code = 200
        encoding = None

        def close(self):
            pass

    class Session:
        def get(self, url, **kwargs):
            return Response()

    def fail_connection(*args):
        stop.set()
        raise PublishFailure("failed")

    monkeypatch.setattr(collector_module, "consume_connection", fail_connection)
    with pytest.raises(PublishFailure):
        run_collector(Collector(object(), "raw"), Session(), "https://example.invalid", stop)


def test_counter_reporter_runs_while_no_connection(caplog):
    class Signal:
        calls = 0

        def wait(self, seconds):
            assert seconds == 30
            self.calls += 1
            return self.calls > 1

    with caplog.at_level("INFO"):
        report_counters(Collector(object(), "raw"), Signal())
    assert "counters" in caplog.text


def test_ack_timeout_is_counted(monkeypatch):
    from ingestion.collector.app import collector as collector_module

    class Response:
        def iter_lines(self, **kwargs):
            return iter(["id: one", "data: {}", ""])

    class Producer:
        def send(self, topic, *, key, value):
            return Future()

    clock = iter([0, 0, 31, 62])
    monkeypatch.setattr(collector_module.time, "monotonic", lambda: next(clock, 100))
    collector = Collector(Producer(), "raw")
    with pytest.raises(PublishFailure):
        consume_connection(Response(), collector, threading.Event())
    assert collector.counters.publish_failed == 1
