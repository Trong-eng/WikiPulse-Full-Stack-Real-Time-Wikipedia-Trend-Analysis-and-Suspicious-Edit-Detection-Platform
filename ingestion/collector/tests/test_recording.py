import json

import pytest

from ingestion.collector.app.collector import Collector
from ingestion.collector.app.recording import Recorder, RecordingError
from ingestion.collector.app.sse import SSEEvent


def test_recording_preserves_title_and_safe_analytics(tmp_path):
    recorder = Recorder(tmp_path / "run.jsonl", tmp_path, secret=b"test-secret")
    event = {"meta": {"id": "event-1", "dt": "2026-01-01T00:00:00Z"},
             "wiki": "enwiki", "title": "Public page", "namespace": 0, "type": "edit",
             "user": "RealEditor", "comment": "Reverted private words", "anon": False,
             "length": {"old": 100, "new": 1}, "revision": {"old": 1, "new": 2}}
    first = recorder.prepare(json.dumps(event))
    second = recorder.prepare(json.dumps(event))
    assert first == second
    recorder.write(first)
    recorder.close()
    saved = json.loads((tmp_path / "run.jsonl").read_text(encoding="utf-8"))
    assert saved["title"] == "Public page"
    assert saved["user"] != "RealEditor"
    assert saved["comment"] == "Reverted"
    assert saved["length"] == event["length"]
    assert "private words" not in json.dumps(saved)


def test_recording_handles_anonymous_and_missing_user(tmp_path):
    recorder = Recorder(tmp_path / "r.jsonl", tmp_path, secret=b"test-secret")
    temporary = recorder.prepare(json.dumps({"user": "~2026-123-456", "title": "x"}))
    missing = recorder.prepare(json.dumps({"title": "x"}))
    assert temporary["anon"] is True
    assert "user" not in missing
    assert recorder.prepare("invalid") is None
    recorder.close()


def test_recording_handles_non_string_type(tmp_path):
    recorder = Recorder(tmp_path / "type.jsonl", tmp_path, secret=b"test-secret")
    assert recorder.prepare('{"type": 12, "comment": "private"}') == {"anon": False}
    recorder.close()


def test_recording_rejects_outside_and_existing_path(tmp_path):
    with pytest.raises(RecordingError):
        Recorder(tmp_path / ".." / "outside.jsonl", tmp_path)
    path = tmp_path / "existing.jsonl"
    path.write_text("preserve", encoding="utf-8")
    with pytest.raises(RecordingError):
        Recorder(path, tmp_path)
    assert path.read_text(encoding="utf-8") == "preserve"


def test_recording_rejects_symlinked_root(tmp_path):
    target = tmp_path / "tracked"
    target.mkdir()
    alias = tmp_path / "recordings"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("filesystem disallows symlink creation")
    with pytest.raises(RecordingError):
        Recorder(alias / "r.jsonl", alias)
    assert not (target / "r.jsonl").exists()


def test_recording_rejects_nested_symlink_inside_root(tmp_path):
    target = tmp_path / "real"
    target.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("filesystem disallows symlink creation")
    with pytest.raises(RecordingError):
        Recorder(alias / "r.jsonl", tmp_path)


def test_recording_only_writes_contiguous_acknowledgements(tmp_path):
    class Future:
        def __init__(self):
            self.is_done = False
            self.exception = None

    class Producer:
        def __init__(self):
            self.futures = []

        def send(self, *args, **kwargs):
            future = Future()
            self.futures.append(future)
            return future

    recorder = Recorder(tmp_path / "r.jsonl", tmp_path, secret=b"secret")
    producer = Producer()
    collector = Collector(producer, "raw", recorder=recorder)
    collector.publish(SSEEvent('{"title":"First"}', "1"))
    collector.publish(SSEEvent('{"title":"Second"}', "2"))
    producer.futures[1].is_done = True
    collector.poll()
    assert (tmp_path / "r.jsonl").read_text() == ""
    producer.futures[0].is_done = True
    collector.poll()
    recorder.close()
    assert [json.loads(line)["title"] for line in (tmp_path / "r.jsonl").read_text().splitlines()] == [
        "First", "Second"
    ]


def test_record_failure_prevents_cursor_advance():
    class Future:
        is_done = True
        exception = None

    class Producer:
        def send(self, *args, **kwargs):
            return Future()

    class RecorderFailure:
        def prepare(self, line):
            return {}

        def write(self, record):
            raise RecordingError("write failed")

    collector = Collector(Producer(), "raw", recorder=RecorderFailure())
    collector.publish(SSEEvent('{}', "1"))
    with pytest.raises(RecordingError):
        collector.poll()
    assert collector.acks.cursor is None
