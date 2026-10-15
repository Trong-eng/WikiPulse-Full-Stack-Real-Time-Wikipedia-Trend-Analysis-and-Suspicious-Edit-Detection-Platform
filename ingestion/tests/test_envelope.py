import json
from datetime import datetime, timezone

import pytest

from ingestion.envelope import collector_version, encode_event, message_key


def test_null_or_missing_wiki_falls_back_to_unknown():
    assert message_key({"wiki": None, "page_id": 10}) == b"unknown:10"
    assert message_key({"page_id": 10}) == b"unknown:10"


def test_page_id_zero_is_kept_and_empty_title_falls_back():
    assert message_key({"wiki": "enwiki", "page_id": 0}) == b"enwiki:0"
    assert message_key({"wiki": "enwiki", "title": ""}) == b"enwiki:unknown"


def test_unicode_title_key_and_payload_roundtrip():
    key, payload = encode_event('{"wiki":"viwiki","title":"Trí tuệ nhân tạo"}',
                                datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert key == "viwiki:Trí tuệ nhân tạo".encode()
    assert json.loads(payload)["title"] == "Trí tuệ nhân tạo"


@pytest.mark.parametrize("line", ["[1, 2]", "42", '"text"', "null"])
def test_non_object_json_passes_through_unkeyed(line):
    assert encode_event(line, datetime.now(timezone.utc)) == (None, line.encode())


def test_collector_version_default_keeps_contract_value(monkeypatch):
    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    assert collector_version("replay") == "replay-0.1.0"
    monkeypatch.setenv("COLLECTOR_VERSION", "0.2.0")
    assert collector_version("live") == "live-0.2.0"


def test_live_source_is_stamped_on_payload(monkeypatch):
    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    _, payload = encode_event('{"wiki":"enwiki","title":"A"}',
                              datetime(2026, 1, 1, tzinfo=timezone.utc), source="live")
    assert json.loads(payload)["collector_version"] == "live-0.1.0"
