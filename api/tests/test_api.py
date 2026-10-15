import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def test_api_import_and_future_route_need_no_cassandra_connection():
    try:
        from api.app.main import app
    except ImportError as exc:
        pytest.fail(f"The real API application is missing: {exc}")
    client = TestClient(app, follow_redirects=False)
    assert client.get("/api/v1/trends").status_code == 501


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


@pytest.mark.parametrize(
    "path, feature",
    [
        ("/api/v1/trends", "trends"),
        ("/api/v1/suspicious-edits", "suspicious-edits"),
        ("/api/v1/events/source-event-id", "events"),
    ],
)
def test_future_endpoints_report_owned_week_two_work(settings, cassandra_boundary, path, feature):
    with client_for(settings) as client:
        response = client.get(path)
        assert response.status_code == 501
        assert response.json() == {
            "code": "NOT_IMPLEMENTED",
            "feature": feature,
            "role": "Cassandra/sink/API",
            "owner": "Nhân",
            "week": 2,
        }
        openapi = client.get("/openapi.json").json()
        route = "/api/v1/events/{event_id}" if feature == "events" else path
        assert "501" in openapi["paths"][route]["get"]["responses"]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"wiki": "unknownwiki"},
        {"wiki": "enwiki' OR 1=1"},
        {"window": "not-a-date"},
        {"window": "2026-01-01T00:00:00"},
    ],
)
def test_invalid_activity_queries_are_rejected(settings, cassandra_boundary, params):
    with client_for(settings) as client:
        assert client.get("/api/v1/activity", params=params).status_code == 422


def test_health_checks_actual_cassandra_readiness(settings, cassandra_boundary):
    with client_for(settings) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "source": "cassandra",
            "pipeline_mode": "REPLAY",
            "implementation_status": "activity_only",
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
            "detail": {"code": "DEPENDENCY_UNAVAILABLE", "source": "cassandra"}
        }
        responses = client.get("/openapi.json").json()["paths"]["/api/v1/activity"]["get"][
            "responses"
        ]
        assert "503" in responses
        assert "422" in responses
