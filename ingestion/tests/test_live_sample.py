"""Guard the LIVE sample: real EventStreams shape, editor names replaced by placeholders.

The sample is pseudonymized, not anonymized: titles, timestamps and revision IDs are real public
Wikipedia data and can be looked up. Rows are deliberately not sorted by meta.dt.
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
    return [line for line in SAMPLE.read_text(encoding="utf-8").splitlines() if line.strip()]


def events():
    return [json.loads(line) for line in lines()]


def allowlisted_edits():
    return [e for e in events() if e.get("wiki") in ("enwiki", "viwiki") and e.get("type") == "edit"]


def test_live_events_have_millisecond_dt_and_no_page_id_or_anon_field():
    for event in events():
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", event["meta"]["dt"])
        assert "page_id" not in event and "anon" not in event


def test_canary_carries_only_schema_and_meta():
    canaries = [e for e in events() if e["meta"].get("domain") == "canary"]
    assert canaries and all(set(c) == {"$schema", "meta"} for c in canaries)


def test_sample_covers_allowlist_types_and_week_two_risk_cases():
    sample = events()
    wikis = {e.get("wiki") for e in sample}
    assert {"enwiki", "viwiki"} <= wikis and wikis - {"enwiki", "viwiki", None}
    assert {"edit", "new", "categorize", "log"} <= {e.get("type") for e in sample}
    edits = allowlisted_edits()
    assert any(e["user"].startswith("~") for e in edits)  # temporary account = LIVE anon editor
    assert any(e["bot"] for e in edits)
    assert any(e["length"]["new"] - e["length"]["old"] <= -1000 for e in edits)  # large deletion
    assert any(re.match(r"Undid revision \d+ by \[\[Special:Contributions/", e["comment"])
               for e in edits)


def test_only_placeholder_users_and_known_fields_remain():
    for event in events():
        assert set(event) <= ALLOWED_KEYS, set(event) - ALLOWED_KEYS
        assert event.get("namespace") not in (2, 3)  # User: / User talk: titles name editors
        if "user" in event:
            assert PLACEHOLDER_USER.fullmatch(event["user"]), event["user"]
        if event.get("type") == "log":
            assert event["log_type"] in NEUTRAL_LOG_TYPES


def test_no_identity_leaks_anywhere_in_raw_lines():
    ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    for line in lines():
        assert not ipv4.search(line)
        assert not re.search(r"User(?:_talk)?:", line)
        for contributor in re.findall(r"Special:Contributions/([^|\]\"]+)", line):
            assert PLACEHOLDER_USER.fullmatch(contributor), contributor
        for temp in re.findall(r"~\d{4}-\d{5}-\d+", line):
            assert PLACEHOLDER_USER.fullmatch(temp), temp
