import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def test_api_import_needs_no_cassandra_connection():
    try:
        from api.app.main import app
    except ImportError as exc:
        pytest.fail(f"The real API application is missing: {exc}")
    paths = TestClient(app, follow_redirects=False).get("/openapi.json").json()["paths"]
    assert {"/api/v1/trends", "/api/v1/suspicious-edits", "/api/v1/events/{event_id}"} <= set(paths)


def client_for(settings):
    from api.app.main import create_app

    return TestClient(create_app(settings=settings))


def test_activity_returns_real_cassandra_rows_and_utc_envelope(
    settings, activity_row, cassandra_boundary
):
    from wikipulse_core.serving import CassandraActivityStore

    CassandraActivityStore(settings).upsert_activity([activity_row])
    with client_for(settings) as client:
        response = client.get("/api/v1/activity", params={"window": "2026-01-01T00:00:00Z"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [
            {
                "wiki": "enwiki",
                "window_start": "2026-01-01T00:00:00Z",
                "window_end": "2026-01-01T00:01:00Z",
                "event_count": 5,
                "edit_count": 3,
                "new_page_count": 2,
                "anonymous_edit_count": 1,
                "bot_edit_count": 1,
                "updated_at": "2026-01-01T00:02:00Z",
            }
        ]
        assert body["source"] == "cassandra"
        assert body["pipeline_mode"] == "REPLAY"
        assert body["provisional"] is True
        assert body["generated_at"].endswith("Z")
    assert all(cluster.closed for cluster in cassandra_boundary.clusters[1:])


def test_empty_activity_is_successful_without_seed_data(settings, cassandra_boundary):
    with client_for(settings) as client:
        response = client.get("/api/v1/activity")
        assert response.status_code == 200
        assert response.json()["data"] == []


def store_for(settings):
    from wikipulse_core.serving import CassandraActivityStore

    return CassandraActivityStore(settings)


def test_trends_return_latest_window_ranked_without_internal_fields(
    settings, cassandra_boundary, trend_row
):
    later = {
        **trend_row,
        "window_start": datetime(2026, 1, 1, 0, 1),
        "window_end": datetime(2026, 1, 1, 0, 6),
    }
    store_for(settings).upsert_trends([
        trend_row,
        {**later, "page_key": "11", "trend_score": 0.02},
        {**later, "page_key": "10", "trend_score": 0.12},
    ])
    with client_for(settings) as client:
        body = client.get("/api/v1/trends", params={"wiki": "enwiki"}).json()
        assert body["window_start"] == "2026-01-01T00:01:00Z"
        assert body["window_end"] == "2026-01-01T00:06:00Z"
        assert [row["page_key"] for row in body["data"]] == ["10", "11"]
        assert set(body["data"][0]) == {
            "wiki", "page_key", "page_title", "namespace", "window_start", "window_end",
            "edit_count", "unique_editors", "abs_byte_delta", "trend_score",
        }
        assert (body["source"], body["pipeline_mode"], body["provisional"]) == (
            "cassandra", "REPLAY", True
        )
        exact = client.get(
            "/api/v1/trends", params={"window": "2026-01-01T07:00:00+07:00", "limit": 1}
        ).json()
        assert exact["window_start"] == "2026-01-01T00:00:00Z"
        assert [row["page_key"] for row in exact["data"]] == ["10"]


def test_empty_trends_report_null_window(settings, cassandra_boundary):
    with client_for(settings) as client:
        response = client.get("/api/v1/trends")
        assert response.status_code == 200
        body = response.json()
        assert (body["data"], body["window_start"], body["window_end"]) == ([], None, None)


def test_suspicious_edits_envelope_has_disclaimer_and_no_user_hash(
    settings, cassandra_boundary, suspicious_row
):
    store_for(settings).upsert_suspicious_edits([
        suspicious_row,
        {**suspicious_row, "event_id": "fixture-005", "risk_score": 20,
         "risk_reasons": ["REVERT_PATTERN"]},
    ])
    with client_for(settings) as client:
        body = client.get("/api/v1/suspicious-edits", params={"min_score": 25}).json()
        assert body["disclaimer"] == "Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."
        assert [row["event_id"] for row in body["data"]] == ["fixture-004"]
        row = body["data"][0]
        assert row["risk_reasons"] == ["LARGE_DELETION"]
        assert row["bucket_start"] == "2026-01-01T00:00:00Z"
        assert "user_hash" not in row
        assert body["provisional"] is True
        empty = client.get("/api/v1/suspicious-edits", params={"wiki": "viwiki"}).json()
        assert empty["data"] == []


def test_event_detail_and_unknown_event(settings, cassandra_boundary, event_row):
    store_for(settings).upsert_events([event_row])
    with client_for(settings) as client:
        response = client.get("/api/v1/events/fixture-004")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["event_id"] == "fixture-004"
        assert body["data"]["risk_reasons"] == ["LARGE_DELETION"]
        assert body["source"] == "cassandra"
        missing = client.get("/api/v1/events/nope")
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "EVENT_NOT_FOUND"
        assert missing.json()["detail"]["message"]


def test_partition_over_capacity_is_reported_not_truncated(
    settings, cassandra_boundary, trend_row
):
    from wikipulse_core.serving import CAPACITY_LIMIT

    store_for(settings).upsert_trends(
        {**trend_row, "page_key": str(n)} for n in range(CAPACITY_LIMIT + 1)
    )
    with client_for(settings) as client:
        response = client.get("/api/v1/trends")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "CAPACITY_EXCEEDED"


@pytest.mark.parametrize(
    "path, params",
    [
        ("/api/v1/activity", {"limit": 0}),
        ("/api/v1/activity", {"limit": 101}),
        ("/api/v1/activity", {"wiki": "unknownwiki"}),
        ("/api/v1/activity", {"wiki": "enwiki' OR 1=1"}),
        ("/api/v1/activity", {"window": "not-a-date"}),
        ("/api/v1/activity", {"window": "2026-01-01T00:00:00"}),
        ("/api/v1/trends", {"limit": 101}),
        ("/api/v1/trends", {"wiki": "dewiki"}),
        ("/api/v1/trends", {"window": "2026-01-01T00:00:00"}),
        ("/api/v1/suspicious-edits", {"minutes": 16}),
        ("/api/v1/suspicious-edits", {"minutes": 0}),
        ("/api/v1/suspicious-edits", {"min_score": 101}),
        ("/api/v1/suspicious-edits", {"window": "yesterday"}),
    ],
)
def test_invalid_queries_use_the_shared_error_shape(settings, cassandra_boundary, path, params):
    with client_for(settings) as client:
        response = client.get(path, params=params)
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "INVALID_QUERY"
        assert detail["message"]
        assert all(set(field) == {"name", "message"} for field in detail["fields"])
        assert detail["fields"]


@pytest.mark.parametrize(
    "path",
    ["/api/v1/activity", "/api/v1/trends", "/api/v1/suspicious-edits", "/api/v1/events/x"],
)
def test_cassandra_outage_is_503_on_every_endpoint(settings, cassandra_boundary, path):
    with client_for(settings) as client:
        cassandra_boundary.query_failure = True
        response = client.get(path)
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert (detail["code"], detail["source"]) == ("DEPENDENCY_UNAVAILABLE", "cassandra")
        assert detail["message"]


def test_error_responses_are_published_in_openapi(settings, cassandra_boundary):
    with client_for(settings) as client:
        paths = client.get("/openapi.json").json()["paths"]
    for route in ("/api/v1/activity", "/api/v1/trends", "/api/v1/suspicious-edits"):
        assert {"422", "503"} <= set(paths[route]["get"]["responses"]), route
    assert {"404", "503"} <= set(paths["/api/v1/events/{event_id}"]["get"]["responses"])


def test_health_checks_actual_cassandra_readiness(settings, cassandra_boundary):
    with client_for(settings) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "source": "cassandra",
            "pipeline_mode": "REPLAY",
            "implementation_status": "activity_trends_suspicious_events",
            "dependencies": {"cassandra": "ready"},
        }
        cassandra_boundary.query_failure = True
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["dependencies"]["cassandra"] == "unavailable"
        assert client.get("/api/v1/activity").status_code == 503


def test_api_starts_unready_and_recovers_when_cassandra_becomes_available(
    settings, cassandra_boundary
):
    cassandra_boundary.connect_failures = 2
    with client_for(settings) as client:
        assert client.get("/health").status_code == 503
        assert client.get("/health").status_code == 200


def test_startup_dependency_warning_is_structured_api_json(settings, cassandra_boundary, capsys):
    cassandra_boundary.connect_failures = 1
    with client_for(settings):
        pass
    lines = capsys.readouterr().err.splitlines()
    assert lines, "API startup must emit a structured readiness failure log"
    record = json.loads(lines[0])
    assert record["service"] == "api"
    assert record["level"] == "WARNING"
    assert "Cassandra" in record["message"]
    assert datetime.fromisoformat(record["timestamp"]).utcoffset() == timedelta(0)


def test_activity_outage_contract_is_published_in_openapi(settings, cassandra_boundary):
    with client_for(settings) as client:
        cassandra_boundary.query_failure = True
        response = client.get("/api/v1/activity")
        assert response.status_code == 503
        assert response.json() == {
            "detail": {
                "code": "DEPENDENCY_UNAVAILABLE",
                "message": "Cassandra is unavailable",
                "source": "cassandra",
            }
        }
        responses = client.get("/openapi.json").json()["paths"]["/api/v1/activity"]["get"][
            "responses"
        ]
        assert "503" in responses
        assert "422" in responses
