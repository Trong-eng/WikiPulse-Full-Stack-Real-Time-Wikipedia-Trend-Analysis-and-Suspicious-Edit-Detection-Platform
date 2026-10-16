"""Unit test cho `replay/replay_producer.py`, chạy không cần Kafka thật.

- Phần đầu: key/envelope, kiểm `--speed`, và `run_replay` (khoảng dòng `[start, end)`, bỏ dòng
  trống, dừng ở lần gửi lỗi đầu tiên, nghỉ sau mỗi lần gửi).
- Phần sau: chạy `main()` với KafkaProducer bị monkeypatch (`FakeProducer` cho các ca thành công,
  lỗi send/flush/close và file BOM; một hàm ném `NoBrokersAvailable` cho exit 3) để kiểm exit
  code 0/1/2/3, `close()` lỗi không che exit code, và file có BOM UTF-8 không mất dòng đầu.
"""

import json
from datetime import datetime, timezone

import pytest


def test_message_key_uses_page_identity_and_title_fallback():
    """Key dùng page_id khi có, không có thì dùng title."""
    from replay.replay_producer import message_key

    assert message_key({"wiki": "enwiki", "page_id": 7, "title": "A"}) == b"enwiki:7"
    assert message_key({"wiki": "viwiki", "title": "B"}) == b"viwiki:B"


def test_envelope_preserves_source_time_and_id():
    """Envelope giữ nguyên meta.id và timestamp gốc, chỉ thêm ingested_at."""
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
    """Dòng JSON hỏng được trả về nguyên văn, không có key, để Spark đưa vào invalid."""
    from replay.replay_producer import encode_event

    key, payload = encode_event("{invalid-json", datetime.now(timezone.utc))
    assert payload == b"{invalid-json"
    assert key is None


@pytest.mark.parametrize("speed", [0, -1, float("nan"), float("inf")])
def test_bad_replay_speed_is_rejected(speed):
    """Speed bằng 0, âm, NaN hoặc vô cực đều bị từ chối."""
    from replay.replay_producer import replay_delay

    with pytest.raises(ValueError):
        replay_delay(1, speed)


def test_speed_only_changes_send_interval():
    """Speed chỉ chia nhỏ thời gian nghỉ: interval 1 s, speed 5 thì nghỉ 0,2 s."""
    from replay.replay_producer import replay_delay

    assert replay_delay(1, 5) == 0.2


LINES = ['{"wiki":"enwiki","page_id":1}', "", "{bad", '{"wiki":"viwiki","title":"B"}']


def fixed_now():
    """Giờ cố định để payload trong test không phụ thuộc đồng hồ máy."""
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_range_is_zero_based_end_exclusive_and_skips_blank_lines():
    """Khoảng `[start, end)` đếm từ 0, không lấy end, và bỏ qua dòng trống."""
    from replay.replay_producer import run_replay

    sent = []
    stats = run_replay(LINES, lambda k, v: sent.append(k), start=1, end=3, now=fixed_now)
    assert sent == [None]  # chỉ có "{bad" (chỉ số 2); chỉ số 1 là dòng trống
    assert (stats.sent, stats.skipped_blank, stats.last_index) == (1, 1, 2)


def test_full_run_sends_every_non_blank_line_in_order():
    """Chạy cả file thì gửi mọi dòng không trống theo đúng thứ tự."""
    from replay.replay_producer import run_replay

    sent = []
    stats = run_replay(LINES, lambda k, v: sent.append(k), now=fixed_now)
    assert sent == [b"enwiki:1", None, b"viwiki:B"]
    assert (stats.sent, stats.last_index) == (3, 3)


def test_send_failure_stops_immediately_with_progress():
    """Lần gửi lỗi đầu tiên dừng ngay và báo ReplaySendError kèm vị trí và tiến độ."""
    from replay.replay_producer import ReplaySendError, run_replay

    calls = []

    def flaky(key, value):
        """Hàm send giả: lỗi ở lần gọi thứ hai."""
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
    """Nghỉ `delay` sau mỗi lần gửi, kể cả lần cuối."""
    from replay.replay_producer import run_replay

    sleeps = []
    run_replay(LINES, lambda k, v: None, delay=0.5, now=fixed_now, sleep=sleeps.append)
    assert sleeps == [0.5, 0.5, 0.5]


def test_main_maps_unreachable_broker_to_exit_3(monkeypatch):
    """Không có broker lúc tạo producer thì thoát mã 3."""
    import kafka
    from kafka.errors import NoBrokersAvailable

    from replay import replay_producer

    def unreachable(**kwargs):
        """KafkaProducer giả luôn báo không có broker."""
        raise NoBrokersAvailable()

    monkeypatch.delenv("PIPELINE_MODE", raising=False)
    monkeypatch.setattr(kafka, "KafkaProducer", unreachable)
    monkeypatch.setattr("sys.argv", ["replay", "--interval", "0"])
    with pytest.raises(SystemExit) as exit_info:
        replay_producer.main()
    assert exit_info.value.code == 3


def test_main_rejects_bad_speed_with_usage_exit(monkeypatch):
    """`--speed 0` là dùng sai, thoát mã 2."""
    from replay import replay_producer

    monkeypatch.setattr("sys.argv", ["replay", "--speed", "0"])
    with pytest.raises(SystemExit) as exit_info:
        replay_producer.main()
    assert exit_info.value.code == 2


def test_replay_stamps_contract_collector_version_by_default(monkeypatch):
    """Mặc định replay gắn `collector_version` đúng contract: `replay-0.1.0`."""
    from replay.replay_producer import encode_event

    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    _, payload = encode_event('{"wiki":"enwiki","title":"A"}', fixed_now())
    assert json.loads(payload)["collector_version"] == "replay-0.1.0"


class FakeProducer:
    """Thay cho kafka.KafkaProducer trong test; lỗi ở các thao tác được cấu hình."""

    instances = []

    def __init__(self, fail_send_at=None, fail_flush=False, fail_close=False, **config):
        """Chọn thao tác sẽ lỗi: lần send thứ `fail_send_at` (đếm từ 1), flush hoặc close."""
        self.fail_send_at, self.fail_flush, self.fail_close = fail_send_at, fail_flush, fail_close
        self.sent, self.closed = [], False
        FakeProducer.instances.append(self)

    def send(self, topic, key=None, value=None):
        """Ghi lại (topic, key); future trả về sẽ lỗi nếu đây là lần send được chọn."""
        from kafka.errors import KafkaTimeoutError

        self.sent.append((topic, key))
        failing = len(self.sent) == self.fail_send_at

        class Future:
            """Future giả do `FakeProducer.send` trả về."""

            def get(self, timeout=None):
                """Như future thật: báo KafkaTimeoutError nếu lần send này được chọn lỗi."""
                if failing:
                    raise KafkaTimeoutError("broker gone")

        return Future()

    def flush(self, timeout=None):
        """Lỗi timeout nếu `fail_flush`."""
        from kafka.errors import KafkaTimeoutError

        if self.fail_flush:
            raise KafkaTimeoutError("flush timed out")

    def close(self, timeout=None):
        """Đánh dấu đã đóng; lỗi timeout nếu `fail_close`."""
        from kafka.errors import KafkaTimeoutError

        self.closed = True
        if self.fail_close:
            raise KafkaTimeoutError("close timed out")


@pytest.fixture
def run_main(monkeypatch, tmp_path):
    """Fixture: tạo file 3 dòng (bỏ dòng trống của LINES, có dòng `{bad`).

    Trả về hàm chạy `main()` với FakeProducer và lấy exit code.
    """
    import kafka

    from replay import replay_producer

    fixture = tmp_path / "events.jsonl"
    fixture.write_text("\n".join(LINES[:1] + LINES[2:]) + "\n", encoding="utf-8")
    FakeProducer.instances = []
    monkeypatch.delenv("PIPELINE_MODE", raising=False)
    monkeypatch.setattr(replay_producer, "configure_logging", lambda service: None)

    def run(*argv, **producer_behaviour):
        """Chạy `main()` với tham số thêm `argv`; `producer_behaviour` truyền cho FakeProducer."""
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
    """Chạy thành công: thoát 0, gửi đủ 3 dòng theo thứ tự và đóng producer."""
    assert run_main() == 0
    producer = FakeProducer.instances[0]
    assert [key for _, key in producer.sent] == [b"enwiki:1", None, b"viwiki:B"]
    assert producer.closed


def test_main_send_failure_exits_1_after_stopping_and_closing(run_main):
    """`send()` lỗi: thoát 1, dừng ngay ở dòng lỗi và vẫn đóng producer."""
    assert run_main(fail_send_at=2) == 1
    producer = FakeProducer.instances[0]
    assert len(producer.sent) == 2
    assert producer.closed


def test_main_flush_failure_exits_1(run_main):
    """`flush()` lỗi cuối lần chạy: thoát 1."""
    assert run_main(fail_flush=True) == 1


def test_main_close_failure_does_not_mask_send_failure(run_main):
    """`close()` lỗi sau khi `send()` lỗi: vẫn thoát 1, không bị che."""
    assert run_main(fail_send_at=1, fail_close=True) == 1


def test_main_missing_file_is_usage_error_before_connecting(run_main, tmp_path):
    """File không tồn tại: thoát 2 và không tạo producer."""
    assert run_main("--file", str(tmp_path / "missing.jsonl")) == 2
    assert FakeProducer.instances == []


def test_main_refuses_live_mode_with_usage_exit(run_main, monkeypatch):
    """PIPELINE_MODE=LIVE: replay từ chối chạy, thoát 2, không tạo producer."""
    monkeypatch.setenv("PIPELINE_MODE", "LIVE")
    assert run_main() == 2
    assert FakeProducer.instances == []


def test_main_reads_utf8_bom_files_without_losing_the_first_record(run_main, tmp_path):
    """File có BOM UTF-8 vẫn đọc đúng dòng đầu tiên."""
    bom_file = tmp_path / "bom.jsonl"
    bom_file.write_text('{"wiki":"enwiki","page_id":1}\n', encoding="utf-8-sig")
    assert run_main("--file", str(bom_file)) == 0
    assert [key for _, key in FakeProducer.instances[0].sent] == [b"enwiki:1"]
