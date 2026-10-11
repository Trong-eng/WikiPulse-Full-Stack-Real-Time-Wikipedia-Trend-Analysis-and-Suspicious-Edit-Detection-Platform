"""Protect smoke isolation at the process/network boundary without starting Docker."""

import io
import json
import re
import subprocess
import urllib.error
from datetime import datetime, timezone

import httpx
import pytest

from scripts import inspect_dashboard, smoke_test


@pytest.fixture
def failed_smoke(monkeypatch, tmp_path):
    calls = []
    # Only deliberate settings belong in failure output; do not capture host secrets.
    monkeypatch.setattr(smoke_test.os, "environ", {})

    def compose_process(command, **kwargs):
        calls.append({"command": command, "env": dict(kwargs["env"])})
        return subprocess.CompletedProcess(
            command, 1 if command[4] == "up" else 0, stdout="controlled startup failure"
        )

    monkeypatch.setattr(smoke_test, "ROOT", tmp_path)
    monkeypatch.setattr(smoke_test.subprocess, "run", compose_process)
    return calls


def test_smoke_overrides_developer_service_endpoints_and_topics(monkeypatch, failed_smoke):
    intended = {
        "PIPELINE_MODE": "REPLAY",
        "API_HOST_PORT": "0",
        "DASHBOARD_HOST_PORT": "0",
        "KAFKA_HOST_PORT": "0",
        "KAFKA_ADVERTISED_EXTERNAL_PORT": "19092",
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "KAFKA_RAW_TOPIC": "wikipedia.recentchange.raw",
        "KAFKA_DLQ_TOPIC": "wikipedia.recentchange.dlq",
        "CASSANDRA_HOST": "cassandra",
        "CASSANDRA_PORT": "9042",
        "CASSANDRA_KEYSPACE": "wikipulse",
        "DASHBOARD_API_URL": "http://api:8000",
        "DATA_BASE_PATH": "file:///data/wikipulse",
        "SPARK_CHECKPOINT_PATH": "/data/checkpoints",
        "TRIGGER_INTERVAL": "5 seconds",
        "WATERMARK_DELAY": "10 minutes",
        "WIKI_ALLOWLIST": "enwiki,viwiki",
        "PIPELINE_VERSION": "0.1.0",
        "USER_HASH_SALT": "local-demo-change-me",
        "MAX_OFFSETS_PER_TRIGGER": "1000",
    }
    for key in intended:
        monkeypatch.setenv(key, "developer-stack-value")
    monkeypatch.setenv("RUN_ID", "dev")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "developer-project")
    monkeypatch.setenv("SMOKE_UNRELATED_SETTING", "preserved")

    with pytest.raises(RuntimeError, match="Compose failed"):
        smoke_test.run_smoke(build=False)

    env = failed_smoke[0]["env"]
    assert {key: env[key] for key in intended} == intended
    assert env["RUN_ID"] != "dev"
    assert env["COMPOSE_PROJECT_NAME"] == f"wikipulse-{env['RUN_ID']}"
    assert env["SMOKE_UNRELATED_SETTING"] == "preserved"


def test_same_second_smokes_use_distinct_projects_and_only_clean_their_own_namespace(
    monkeypatch, failed_smoke, tmp_path
):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(smoke_test, "datetime", FrozenDatetime)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="Compose failed"):
            smoke_test.run_smoke(build=False)

    starts = [call for call in failed_smoke if call["command"][4] == "up"]
    run_ids = [call["env"]["RUN_ID"] for call in starts]
    assert len(set(run_ids)) == 2
    assert all(re.fullmatch(r"smoke-20260101000000-[a-f0-9]+", run_id) for run_id in run_ids)
    projects = {call["env"]["COMPOSE_PROJECT_NAME"] for call in starts}
    cleanup_projects = {
        call["command"][3] for call in failed_smoke if call["command"][4] == "down"
    }
    assert cleanup_projects == projects
    for call in failed_smoke:
        assert call["command"][:3] == ["docker", "compose", "-p"]
        assert call["command"][3] == call["env"]["COMPOSE_PROJECT_NAME"]
    assert all((tmp_path / "artifacts" / run_id / "report.json").is_file() for run_id in run_ids)


def test_smoke_executes_dashboard_inspection_after_stable_activity(monkeypatch, tmp_path):
    rows = [
        {
            "wiki": "enwiki", "event_count": 5, "edit_count": 5, "new_page_count": 0,
            "anonymous_edit_count": 1, "bot_edit_count": 1,
        },
        {
            "wiki": "viwiki", "event_count": 1, "edit_count": 0, "new_page_count": 1,
            "anonymous_edit_count": 0, "bot_edit_count": 0,
        },
    ]
    fixture_dir = tmp_path / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "expected_activity.json").write_text(
        json.dumps({"phase_one_records": 10, "rows": rows}), encoding="utf-8"
    )
    boundaries = []

    def compose_process(command, **kwargs):
        args = command[4:]
        boundaries.append(args)
        if args[:2] == ["port", "api"]:
            output = "127.0.0.1:18001"
        elif args[:2] == ["port", "dashboard"]:
            output = "127.0.0.1:18501"
        elif args[:4] == ["exec", "-T", "spark", "cat"]:
            output = json.dumps({
                "active_queries": {"activity_gold": True},
                "queries": {"activity_gold": {"eventTime": {
                    "watermark": "2026-01-01T00:01:00+00:00"
                }}},
            })
        elif (
            args[:1] in [["up"], ["run"], ["logs"], ["down"]]
            or args[:5] == ["exec", "-T", "spark", "python", "scripts/inspect_lake.py"]
            or args == ["exec", "-T", "dashboard", "python", "scripts/inspect_dashboard.py"]
        ):
            output = "passed"
        else:
            pytest.fail(f"Unexpected Compose action: {args}")
        return subprocess.CompletedProcess(command, 0, stdout=output)

    def api_response(url, **kwargs):
        if "/api/v1/activity" in url:
            boundaries.append(["activity", url])
            selected = rows[1] if "wiki=viwiki" in url else rows[0]
            output = json.dumps({
                "data": [{
                    **selected, "window_start": "2026-01-01T00:00:00Z",
                    "window_end": "2026-01-01T00:01:00Z", "updated_at": "2026-01-01T00:01:10Z",
                }],
                "generated_at": "2026-01-01T00:01:15Z", "source": "cassandra",
                "pipeline_mode": "REPLAY", "provisional": True,
            })
        elif url.endswith("/_stcore/health"):
            output = "ok"
        elif url.endswith("/health"):
            output = json.dumps({
                "status": "ok", "source": "cassandra", "pipeline_mode": "REPLAY",
                "implementation_status": "activity_only", "dependencies": {"cassandra": "ready"},
            })
        else:
            raise urllib.error.HTTPError(url, 501, "deferred", None, None)
        return io.BytesIO(output.encode())

    monkeypatch.setattr(smoke_test, "ROOT", tmp_path)
    monkeypatch.setattr(smoke_test.subprocess, "run", compose_process)
    monkeypatch.setattr(smoke_test.urllib.request, "urlopen", api_response)
    report = smoke_test.run_smoke(build=False)

    inspection = ["exec", "-T", "dashboard", "python", "scripts/inspect_dashboard.py"]
    assert inspection in boundaries
    assert boundaries.index(inspection) > max(
        index for index, boundary in enumerate(boundaries) if boundary[0] == "activity"
    )
    assert report["status"] == "passed"


def test_dashboard_inspector_selects_fixture_instant_from_iso_z_wire_values(monkeypatch):
    expected = json.loads(
        (inspect_dashboard.ROOT / "tests/fixtures/expected_activity.json").read_text()
    )
    original_client = httpx.Client

    def serve(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={
                "status": "ok", "source": "cassandra", "pipeline_mode": "REPLAY",
                "implementation_status": "activity_only", "dependencies": {"cassandra": "ready"},
            })
        assert request.url.path == "/api/v1/activity", request.url
        wiki = request.url.params["wiki"]
        wanted = next(row for row in expected["rows"] if row["wiki"] == wiki)
        original = {
            **wanted, "window_start": "2026-01-01T00:00:00Z",
            "window_end": "2026-01-01T00:01:00Z", "updated_at": "2026-10-11T01:02:03Z",
        }
        # A newer, different count proves the inspector actively selects the original window.
        newer = {
            **original, "window_start": "2026-01-01T00:20:00Z",
            "window_end": "2026-01-01T00:21:00Z", "event_count": 99,
        }
        return httpx.Response(200, json={
            "data": [newer, original], "generated_at": "2026-10-11T01:02:04Z",
            "source": "cassandra", "pipeline_mode": "REPLAY", "provisional": True,
        })

    transport = httpx.MockTransport(serve)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original_client(**{**kwargs, "transport": transport})
    )
    monkeypatch.setenv("DASHBOARD_API_URL", "http://fixture-api:8000")
    monkeypatch.setenv("WIKI_ALLOWLIST", "enwiki,viwiki")
    monkeypatch.setenv("PIPELINE_MODE", "REPLAY")
    report = inspect_dashboard.inspect_dashboard()

    assert report["status"] == "passed"
    assert report["overview"]["enwiki"]["window_start"] == "2026-01-01T00:00:00Z"
    assert report["overview"]["viwiki"]["window_start"] == "2026-01-01T00:00:00Z"
    assert report["readiness"] == {"API · readiness": "HTTP 200", "Cassandra": "ready"}
