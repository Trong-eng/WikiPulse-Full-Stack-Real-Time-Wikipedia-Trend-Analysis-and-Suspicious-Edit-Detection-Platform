"""Unit test cho `ingestion/envelope.py`.

Kiểm cách tạo key Kafka (fallback `unknown` khi wiki thiếu/null, giữ page_id 0, title rỗng thành
`unknown`), payload giữ nguyên Unicode, `collector_version` theo `source` và biến
`COLLECTOR_VERSION`, JSON hợp lệ nhưng không phải object thì trả về nguyên văn không có key, và
surrogate lẻ vẫn được gắn key và metadata thay vì crash. Ca JSON hỏng được test ở
`replay/tests/test_replay.py`.
"""

import json
from datetime import datetime, timezone

import pytest

from ingestion.envelope import collector_version, encode_event, message_key


def test_null_or_missing_wiki_falls_back_to_unknown():
    """wiki null hoặc thiếu thì key dùng `unknown`."""
    assert message_key({"wiki": None, "page_id": 10}) == b"unknown:10"
    assert message_key({"page_id": 10}) == b"unknown:10"


def test_page_id_zero_is_kept_and_empty_title_falls_back():
    """page_id 0 vẫn được giữ; title rỗng thì thành `unknown`."""
    assert message_key({"wiki": "enwiki", "page_id": 0}) == b"enwiki:0"
    assert message_key({"wiki": "enwiki", "title": ""}) == b"enwiki:unknown"


def test_unicode_title_key_and_payload_roundtrip():
    """Title tiếng Việt giữ nguyên trong key và payload."""
    key, payload = encode_event('{"wiki":"viwiki","title":"Trí tuệ nhân tạo"}',
                                datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert key == "viwiki:Trí tuệ nhân tạo".encode()
    assert json.loads(payload)["title"] == "Trí tuệ nhân tạo"


@pytest.mark.parametrize("line", ["[1, 2]", "42", '"text"', "null"])
def test_non_object_json_passes_through_unkeyed(line):
    """JSON hợp lệ nhưng không phải object thì trả về nguyên văn, không có key."""
    assert encode_event(line, datetime.now(timezone.utc)) == (None, line.encode())


def test_collector_version_default_keeps_contract_value(monkeypatch):
    """Mặc định ra `replay-0.1.0`; đặt COLLECTOR_VERSION thì đổi theo."""
    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    assert collector_version("replay") == "replay-0.1.0"
    monkeypatch.setenv("COLLECTOR_VERSION", "0.2.0")
    assert collector_version("live") == "live-0.2.0"


def test_live_source_is_stamped_on_payload(monkeypatch):
    """source=live thì payload có `collector_version` là `live-0.1.0`."""
    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    _, payload = encode_event('{"wiki":"enwiki","title":"A"}',
                              datetime(2026, 1, 1, tzinfo=timezone.utc), source="live")
    assert json.loads(payload)["collector_version"] == "live-0.1.0"


def test_lone_surrogate_is_still_stamped_and_keyed_instead_of_crashing(monkeypatch):
    """Surrogate lẻ không làm crash: vẫn có key, metadata và payload JSON hợp lệ."""
    monkeypatch.delenv("COLLECTOR_VERSION", raising=False)
    # Escape JSON hợp lệ, nhưng decode ra surrogate lẻ nên không mã hoá được UTF-8.
    line = r'{"wiki":"enwiki","title":"\ud800"}'
    key, payload = encode_event(line, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert key == rb"enwiki:\ud800"
    assert rb'"title": "\ud800"' in payload  # dạng ASCII-escape vẫn là JSON hợp lệ
    document = json.loads(payload)
    assert document["collector_version"] == "replay-0.1.0"
    assert document["ingested_at"] == "2026-01-01T00:00:00+00:00"


def test_payload_keeps_unicode_unescaped():
    """Trường hợp thường, payload giữ Unicode thật, không escape `\\u`."""
    _, payload = encode_event('{"wiki":"viwiki","title":"Trí tuệ"}',
                              datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert "Trí tuệ".encode() in payload
