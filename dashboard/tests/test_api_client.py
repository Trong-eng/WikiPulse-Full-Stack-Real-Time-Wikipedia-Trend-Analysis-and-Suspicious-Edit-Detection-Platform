"""The dashboard's HTTP boundary uses contract responses, never a live API."""

import httpx
import pytest

try:
    from dashboard.api_client import APIClient
except ModuleNotFoundError:
    APIClient = None


ACTIVITY_ROW = {
    "wiki": "enwiki",
    "window_start": "2026-09-28T10:00:00Z",
    "window_end": "2026-09-28T10:01:00Z",
    "event_count": 7,
    "edit_count": 5,
    "new_page_count": 2,
    "anonymous_edit_count": 3,
    "bot_edit_count": 1,
    "updated_at": "2026-09-28T10:01:08Z",
}


def activity_payload(rows=None):
    return {
        "data": [dict(ACTIVITY_ROW)] if rows is None else rows,
        "generated_at": "2026-09-28T10:02:00Z",
        "source": "cassandra",
        "pipeline_mode": "REPLAY",
        "provisional": True,
    }


def client_for(handler, timeout=5.0):
    assert APIClient is not None, "Dashboard API client has not been implemented"
    return APIClient(
        "http://api:8000", timeout=timeout, transport=httpx.MockTransport(handler)
    )


def test_activity_queries_selected_wiki_window_and_limit():
    requests = []

    def serve(request):
        requests.append(request)
        return httpx.Response(200, json=activity_payload())

    result = client_for(serve).get_activity(
        "enwiki", window="2026-09-28T10:00:00Z", limit=20
    )

    assert result.state == "ok"
    assert result.payload["data"][0]["event_count"] == 7
    assert str(requests[0].url).startswith("http://api:8000/api/v1/activity?")
    assert dict(requests[0].url.params) == {
        "wiki": "enwiki",
        "window": "2026-09-28T10:00:00Z",
        "limit": "20",
    }


def test_empty_activity_stays_empty_instead_of_inventing_zero_counts():
    result = client_for(lambda _: httpx.Response(200, json=activity_payload([]))).get_activity(
        "viwiki"
    )

    assert result.state == "empty"
    assert result.payload["data"] == []
    assert result.status_code == 200


def test_timeout_is_distinct_from_an_empty_dataset_and_sets_request_timeout():
    requests = []

    def time_out(request):
        requests.append(request)
        raise httpx.ReadTimeout("slow dependency", request=request)

    result = client_for(time_out, timeout=2.5).get_activity("enwiki")

    assert result.state == "unavailable"
    assert result.status_code is None
    assert result.payload is None
    assert "quá thời gian" in result.message.lower()
    assert requests[0].extensions["timeout"]["read"] == 2.5


def test_connection_failure_has_no_success_or_empty_payload():
    def disconnected(request):
        raise httpx.ConnectError("connection refused", request=request)

    result = client_for(disconnected).get_health()

    assert result.state == "unavailable"
    assert result.payload is None
    assert "kết nối" in result.message.lower()


def test_cassandra_readiness_failure_preserves_actual_health_response():
    health = {
        "status": "unavailable",
        "pipeline_mode": "REPLAY",
        "dependencies": {"cassandra": "unavailable"},
        "implementation_status": "activity_only",
    }
    result = client_for(lambda _: httpx.Response(503, json=health)).get_health()

    assert result.state == "unavailable"
    assert result.status_code == 503
    assert result.payload == health


def test_health_uses_the_readiness_route():
    paths = []

    def serve(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={"status": "ok", "cassandra": "ready"})

    result = client_for(serve).get_health()

    assert result.state == "ok"
    assert paths == ["/health"]


@pytest.mark.parametrize(
    ("method", "arguments", "path"),
    [
        ("get_trends", ("viwiki",), "/api/v1/trends"),
        ("get_suspicious_edits", ("viwiki",), "/api/v1/suspicious-edits"),
        ("get_event", ("abc-123",), "/api/v1/events/abc-123"),
    ],
)
def test_future_endpoints_keep_http501_and_owner_week(method, arguments, path):
    requests = []
    detail = {"code": "NOT_IMPLEMENTED", "owner": "Nhân", "planned_week": 2}

    def serve(request):
        requests.append(request)
        return httpx.Response(501, json={"detail": detail})

    client = client_for(serve)
    result = getattr(client, method)(*arguments)

    assert result.state == "not_implemented"
    assert result.status_code == 501
    assert result.payload["detail"] == detail
    assert requests[0].url.path == path
    if method != "get_event":
        assert dict(requests[0].url.params) == {"wiki": "viwiki"}


def test_http_error_preserves_status_and_does_not_return_activity():
    result = client_for(
        lambda _: httpx.Response(422, json={"detail": "Invalid window"})
    ).get_activity("enwiki")

    assert result.state == "error"
    assert result.status_code == 422
    assert "422" in result.message


def test_invalid_json_is_a_renderable_error_state():
    result = client_for(
        lambda _: httpx.Response(200, text="not JSON")
    ).get_activity("enwiki")

    assert result.state == "error"
    assert "json" in result.message.lower()


@pytest.mark.parametrize(
    "change",
    [
        {"data": [{}]},
        {"data": [{**ACTIVITY_ROW, "wiki": "viwiki"}]},
        {"data": [{**ACTIVITY_ROW, "event_count": "7"}]},
        {"data": [{**ACTIVITY_ROW, "event_count": -1}]},
        {"data": [{**ACTIVITY_ROW, "window_start": "not-a-timestamp"}]},
        {"generated_at": "2026-09-28T10:02:00"},
        {"pipeline_mode": "UNKNOWN"},
        {"pipeline_mode": ["REPLAY"]},
        {"pipeline_mode": {"mode": "REPLAY"}},
        {"provisional": "true"},
    ],
)
def test_invalid_activity_contract_never_reaches_metric_rendering(change):
    result = client_for(
        lambda _: httpx.Response(200, json={**activity_payload(), **change})
    ).get_activity("enwiki")

    assert result.state == "error"
    assert "contract" in result.message.lower()


def test_non_object_payload_is_a_renderable_error_state():
    result = client_for(lambda _: httpx.Response(200, json=[])).get_health()

    assert result.state == "error"
    assert result.status_code == 200
