"""Test bảo vệ file mẫu LIVE `tests/fixtures/recentchange_live_sample.jsonl`.

File mẫu gồm các event thật lấy từ spike EventStreams, tên người sửa đã thay bằng placeholder
(`LiveSampleUserN`, `~2026-00000-N`). Các test kiểm hai việc:
- Shape: giữ đúng đặc điểm của dữ liệu LIVE mà collector tuần 2 phải xử lý (meta.dt có mili-giây,
  không có page_id/anon, canary chỉ có `$schema` + `meta`, đủ các loại event và ca rủi ro).
- Privacy: field `user` chỉ là placeholder, chỉ có field trong allowlist, loại namespace 2/3 và
  chỉ cho log_type trung tính. Ngoài ra quét toàn bộ dòng raw: không có IPv4, không có
  `User:`/`User_talk:`, tên trong link `Special:Contributions/` và tài khoản tạm `~YYYY-NNNNN-N`
  đều phải là placeholder.

Mẫu được pseudonymize chứ không ẩn danh hoàn toàn: title, timestamp và revision ID là dữ liệu
Wikipedia công khai, tra lại được. Các dòng cố ý không sắp xếp theo meta.dt.
"""

import json
import re
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2] / "tests/fixtures/recentchange_live_sample.jsonl"
PLACEHOLDER_USER = re.compile(r"LiveSampleUser\d+|~2026-00000-\d+")
ALLOWED_KEYS = {
    "$schema", "meta", "id", "type", "namespace", "title", "title_url", "comment", "timestamp",
    "user", "bot", "notify_url", "minor", "patrolled", "length", "revision", "server_url",
    "server_name", "server_script_path", "wiki", "parsedcomment", "log_id", "log_type",
    "log_action", "log_params", "log_action_comment",
}
NEUTRAL_LOG_TYPES = {"move", "patrol", "create", "upload", "protect"}


def lines():
    """Các dòng không trống của file mẫu LIVE."""
    return [line for line in SAMPLE.read_text(encoding="utf-8").splitlines() if line.strip()]


def events():
    """File mẫu đã parse thành list dict."""
    return [json.loads(line) for line in lines()]


def allowlisted_edits():
    """Các event edit thuộc enwiki hoặc viwiki."""
    return [e for e in events() if e.get("wiki") in ("enwiki", "viwiki") and e.get("type") == "edit"]


def test_live_events_have_millisecond_dt_and_no_page_id_or_anon_field():
    """Event LIVE có meta.dt dạng mili-giây và không có field page_id hay anon."""
    for event in events():
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", event["meta"]["dt"])
        assert "page_id" not in event and "anon" not in event


def test_canary_carries_only_schema_and_meta():
    """Có ít nhất một event canary, và mọi canary chỉ có `$schema` và `meta`."""
    canaries = [e for e in events() if e["meta"].get("domain") == "canary"]
    assert canaries and all(set(c) == {"$schema", "meta"} for c in canaries)


def test_sample_covers_allowlist_types_and_week_two_risk_cases():
    """Mẫu có enwiki, viwiki và ít nhất một wiki ngoài allowlist; đủ loại edit/new/categorize/log;
    và các ca rủi ro tuần 2: tài khoản tạm, bot, xoá lớn (>= 1000 byte), undo/revert.
    """
    sample = events()
    wikis = {e.get("wiki") for e in sample}
    assert {"enwiki", "viwiki"} <= wikis and wikis - {"enwiki", "viwiki", None}
    assert {"edit", "new", "categorize", "log"} <= {e.get("type") for e in sample}
    edits = allowlisted_edits()
    assert any(e["user"].startswith("~") for e in edits)  # tài khoản tạm = ẩn danh ở LIVE
    assert any(e["bot"] for e in edits)
    assert any(e["length"]["new"] - e["length"]["old"] <= -1000 for e in edits)  # xoá lớn
    assert any(re.match(r"Undid revision \d+ by \[\[Special:Contributions/", e["comment"])
               for e in edits)


def test_only_placeholder_users_and_known_fields_remain():
    """Chỉ còn user placeholder, field trong allowlist, không trang User và log_type trung tính."""
    for event in events():
        assert set(event) <= ALLOWED_KEYS, set(event) - ALLOWED_KEYS
        assert event.get("namespace") not in (2, 3)  # trang User: / User talk: lộ tên người sửa
        if "user" in event:
            assert PLACEHOLDER_USER.fullmatch(event["user"]), event["user"]
        if event.get("type") == "log":
            assert event["log_type"] in NEUTRAL_LOG_TYPES


def test_no_identity_leaks_anywhere_in_raw_lines():
    """Quét dòng raw: không IPv4, không `User:`/`User_talk:`.

    Tên trong link `Special:Contributions/` và tài khoản tạm đều phải là placeholder.
    """
    ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    for line in lines():
        assert not ipv4.search(line)
        assert not re.search(r"User(?:_talk)?:", line)
        for contributor in re.findall(r"Special:Contributions/([^|\]\"]+)", line):
            assert PLACEHOLDER_USER.fullmatch(contributor), contributor
        for temp in re.findall(r"~\d{4}-\d{5}-\d+", line):
            assert PLACEHOLDER_USER.fullmatch(temp), temp
