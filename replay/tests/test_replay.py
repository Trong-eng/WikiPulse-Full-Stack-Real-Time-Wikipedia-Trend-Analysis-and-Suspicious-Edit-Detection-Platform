import json
from datetime import datetime, timezone

import pytest


def test_message_key_uses_page_identity_and_title_fallback():
    from replay.replay_producer import message_key

    assert message_key({"wiki": "enwiki", "page_id": 7, "title": "A"}) == b"enwiki:7"
    assert message_key({"wiki": "viwiki", "title": "B"}) == b"viwiki:B"


def test_envelope_preserves_source_time_and_id():
    from replay.replay_producer import encode_event

    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    raw = '{"meta":{"id":"stable"},"wiki":"enwiki","timestamp":1767225610}'
    key, payload = encode_event(raw, now)
    value = json.loads(payload)
    assert value["meta"]["id"] == "stable"
    assert value["timestamp"] == 1767225610
    assert value["ingested_at"] == "2026-10-11T00:00:00+00:00"
    assert key == b"enwiki:unknown"


def test_malformed_fixture_can_exercise_invalid_sink():
    from replay.replay_producer import encode_event

    key, payload = encode_event("{invalid-json", datetime.now(timezone.utc))
    assert payload == b"{invalid-json"
    assert key is None


@pytest.mark.parametrize("speed", [0, -1, float("nan"), float("inf")])
def test_bad_replay_speed_is_rejected(speed):
    from replay.replay_producer import replay_delay

    with pytest.raises(ValueError):
        replay_delay(1, speed)


def test_speed_only_changes_send_interval():
    from replay.replay_producer import replay_delay

    assert replay_delay(1, 5) == 0.2


LINES = ['{"wiki":"enwiki","page_id":1}', "", "{bad", '{"wiki":"viwiki","title":"B"}']


def fixed_now():
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_range_is_zero_based_end_exclusive_and_skips_blank_lines():
    from replay.replay_producer import run_replay

    sent = []
    stats = run_replay(LINES, lambda k, v: sent.append(k), start=1, end=3, now=fixed_now)
    assert sent == [None]  # only "{bad" (index 2); index 1 is blank
    assert (stats.sent, stats.skipped_blank, stats.last_index) == (1, 1, 2)


def test_full_run_sends_every_non_blank_line_in_order():
    from replay.replay_producer import run_replay

    sent = []
    stats = run_replay(LINES, lambda k, v: sent.append(k), now=fixed_now)
    assert sent == [b"enwiki:1", None, b"viwiki:B"]
    assert (stats.sent, stats.last_index) == (3, 3)


def test_send_failure_stops_immediately_with_progress():
    from replay.replay_producer import ReplaySendError, run_replay

    calls = []

    def flaky(key, value):
        calls.append(key)
        if len(calls) == 2:
            raise TimeoutError("broker gone")

    with pytest.raises(ReplaySendError) as err:
        run_replay(LINES, flaky, now=fixed_now)
    assert err.value.stats.sent == 1
    assert err.value.stats.last_index == 0
    assert isinstance(err.value.__cause__, TimeoutError)
    assert err.value.index == 2
    assert len(calls) == 2


def test_delay_follows_each_send():
    from replay.replay_producer import run_replay

    sleeps = []
    run_replay(LINES, lambda k, v: None, delay=0.5, now=fixed_now, sleep=sleeps.append)
    assert sleeps == [0.5, 0.5, 0.5]


def test_main_maps_unreachable_broker_to_exit_3(monkeypatch):
    import kafka
    from kafka.errors import NoBrokersAvailable

    from replay import replay_producer

    def unreachable(**kwargs):
        raise NoBrokersAvailable()

    monkeypatch.delenv("PIPELINE_MODE", raising=False)
    monkeypatch.setattr(kafka, "KafkaProducer", unreachable)
    monkeypatch.setattr("sys.argv", ["replay", "--interval", "0"])
    with pytest.raises(SystemExit) as exit_info:
        replay_producer.main()
    assert exit_info.value.code == 3


def test_main_rejects_bad_speed_with_usage_exit(monkeypatch):
    from replay import replay_producer

    monkeypatch.setattr("sys.argv", ["replay", "--speed", "0"])
    with pytest.raises(SystemExit) as exit_info:
        replay_producer.main()
    assert exit_info.value.code == 2


def test_replay_stamps_contract_collector_version_by_default(monkeypatch):
    from replay.replay_producer import encode_event

    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    _, payload = encode_event('{"wiki":"enwiki","title":"A"}', fixed_now())
    assert json.loads(payload)["collector_version"] == "replay-0.1.0"


class FakeProducer:
    """Stands in for kafka.KafkaProducer; fails the configured operations."""

    instances = []

    def __init__(self, fail_send_at=None, fail_flush=False, fail_close=False, **config):
        self.fail_send_at, self.fail_flush, self.fail_close = fail_send_at, fail_flush, fail_close
        self.sent, self.closed = [], False
        FakeProducer.instances.append(self)

    def send(self, topic, key=None, value=None):
        from kafka.errors import KafkaTimeoutError

        self.sent.append((topic, key))
        failing = len(self.sent) == self.fail_send_at

        class Future:
            def get(self, timeout=None):
                if failing:
                    raise KafkaTimeoutError("broker gone")

        return Future()

    def flush(self, timeout=None):
        from kafka.errors import KafkaTimeoutError

        if self.fail_flush:
            raise KafkaTimeoutError("flush timed out")

    def close(self, timeout=None):
        from kafka.errors import KafkaTimeoutError

        self.closed = True
        if self.fail_close:
            raise KafkaTimeoutError("close timed out")


@pytest.fixture
def run_main(monkeypatch, tmp_path):
    import kafka

    from replay import replay_producer

    fixture = tmp_path / "events.jsonl"
    fixture.write_text("\n".join(LINES[:1] + LINES[2:]) + "\n", encoding="utf-8")
    FakeProducer.instances = []
    monkeypatch.delenv("PIPELINE_MODE", raising=False)
    monkeypatch.setattr(replay_producer, "configure_logging", lambda service: None)

    def run(*argv, **producer_behaviour):
        monkeypatch.setattr(kafka, "KafkaProducer",
                            lambda **config: FakeProducer(**producer_behaviour, **config))
        monkeypatch.setattr("sys.argv", ["replay", "--file", str(fixture), "--interval", "0", *argv])
        try:
            replay_producer.main()
        except SystemExit as exc:
            return exc.code
        return 0

    return run


def test_main_success_sends_all_records_and_closes(run_main):
    assert run_main() == 0
    producer = FakeProducer.instances[0]
    assert [key for _, key in producer.sent] == [b"enwiki:1", None, b"viwiki:B"]
    assert producer.closed


def test_main_send_failure_exits_1_after_stopping_and_closing(run_main):
    assert run_main(fail_send_at=2) == 1
    producer = FakeProducer.instances[0]
    assert len(producer.sent) == 2
    assert producer.closed


def test_main_flush_failure_exits_1(run_main):
    assert run_main(fail_flush=True) == 1


def test_main_close_failure_does_not_mask_send_failure(run_main):
    assert run_main(fail_send_at=1, fail_close=True) == 1


def test_main_missing_file_is_usage_error_before_connecting(run_main, tmp_path):
    assert run_main("--file", str(tmp_path / "missing.jsonl")) == 2
    assert FakeProducer.instances == []


def test_main_refuses_live_mode_with_usage_exit(run_main, monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", "LIVE")
    assert run_main() == 2
    assert FakeProducer.instances == []


def test_main_reads_utf8_bom_files_without_losing_the_first_record(run_main, tmp_path):
    bom_file = tmp_path / "bom.jsonl"
    bom_file.write_text('{"wiki":"enwiki","page_id":1}\n', encoding="utf-8-sig")
    assert run_main("--file", str(bom_file)) == 0
    assert [key for _, key in FakeProducer.instances[0].sent] == [b"enwiki:1"]
