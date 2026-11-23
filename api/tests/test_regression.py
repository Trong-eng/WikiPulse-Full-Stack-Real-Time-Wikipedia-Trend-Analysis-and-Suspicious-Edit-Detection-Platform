"""W4-NHAN-01 regression guards: the published API and the CQL must not drift silently."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "api" / "openapi.json"


def current_openapi(settings):
    from api.app.main import create_app

    return create_app(settings=settings).openapi()


def test_openapi_matches_the_committed_snapshot(settings):
    """Any schema change must update api/openapi.json (and docs/contracts.md) in the same PR.

    Regenerate: UPDATE_OPENAPI=1 python -m pytest api/tests/test_regression.py
    """
    schema = current_openapi(settings)
    if os.environ.get("UPDATE_OPENAPI") == "1":
        SNAPSHOT.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    assert json.loads(SNAPSHOT.read_text(encoding="utf-8")) == schema


def test_openapi_documents_every_error_code(settings):
    schema = current_openapi(settings)
    codes = schema["components"]["schemas"]["ErrorDetail"]["properties"]["code"]["enum"]
    assert set(codes) == {
        "INVALID_QUERY", "EVENT_NOT_FOUND", "DEPENDENCY_UNAVAILABLE", "CAPACITY_EXCEEDED"
    }
    for path, item in schema["paths"].items():
        if path.startswith("/api/v1/"):
            assert "503" in item["get"]["responses"], path
            assert item["get"].get("description"), path


def cql_columns():
    text = (ROOT / "storage" / "cassandra" / "schema.cql").read_text(encoding="utf-8")
    tables = {}
    for name, body in re.findall(r"__KEYSPACE__\.(\w+) \((.*?)\n\)", text, re.S):
        columns = []
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if line and not line.startswith(("PRIMARY KEY", "--")):
                columns.append(line.split()[0])
        tables[name] = columns
    return tables


def test_cql_columns_match_the_store_models():
    from wikipulse_core import serving

    tables = cql_columns()
    expected = {
        "wiki_activity_by_window": serving.ACTIVITY_FIELDS,
        "page_trends_by_window": serving.TREND_FIELDS,
        "suspicious_edits_by_bucket": serving.SUSPICIOUS_FIELDS,
        "events_by_id": serving.EVENT_FIELDS,
        "trend_windows_by_wiki": ("wiki", "window_start", "updated_at"),
        "suspicious_buckets_by_wiki": ("wiki", "bucket_start", "updated_at"),
    }
    assert set(tables) == set(expected)
    for table, fields in expected.items():
        assert set(tables[table]) == set(fields), table


def test_data_dictionary_lists_every_serving_table():
    dictionary = (ROOT / "docs" / "data-dictionary.md").read_text(encoding="utf-8")
    for table in cql_columns():
        if table != "wiki_activity_by_window":  # Listed as Cassandra/activity since CP0.
            assert f"Cassandra/{table}" in dictionary, table
