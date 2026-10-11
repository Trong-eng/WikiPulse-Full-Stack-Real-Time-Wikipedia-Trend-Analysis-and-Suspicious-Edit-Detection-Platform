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
