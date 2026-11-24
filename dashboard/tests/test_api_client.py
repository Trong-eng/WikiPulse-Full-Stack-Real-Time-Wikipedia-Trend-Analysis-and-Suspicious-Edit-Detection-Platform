"""The dashboard's HTTP boundary uses contract responses, never a live API."""

import httpx
import pytest

from dashboard.api_client import DISCLAIMER_TEXT, APIClient

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

TREND_ROW = {
    "wiki": "enwiki",
    "page_key": "42",
    "page_title": "Python (programming language)",
    "namespace": 0,
    "window_start": "2026-09-28T10:00:00Z",
    "window_end": "2026-09-28T10:05:00Z",
    "edit_count": 12,
    "unique_editors": 5,
    "abs_byte_delta": 1400,
    "trend_score": 0.85,
}

SUSPICIOUS_ROW = {
    "wiki": "enwiki",
    "event_id": "evt-123",
    "bucket_start": "2026-09-28T10:00:00Z",
    "event_time": "2026-09-28T10:00:15Z",
    "page_key": "42",
    "page_title": "Python (programming language)",
    "revision_new": 999002,
    "byte_delta": -1500,
    "is_anonymous": True,
    "is_bot": False,
    "risk_score": 60,
    "risk_reasons": ["LARGE_DELETION", "ANONYMOUS_EDIT"],
    "updated_at": "2026-09-28T10:00:25Z",
}

EVENT_DETAIL_ROW = {
    "event_id": "evt-123",
    "wiki": "enwiki",
    "event_time": "2026-09-28T10:00:15Z",
    "page_key": "42",
    "page_title": "Python (programming language)",
    "namespace": 0,
    "event_type": "edit",
    "revision_old": 999001,
    "revision_new": 999002,
    "length_old": 5000,
    "length_new": 3500,
    "byte_delta": -1500,
    "is_anonymous": True,
    "is_bot": False,
    "is_minor": False,
    "risk_score": 60,
    "risk_reasons": ["LARGE_DELETION", "ANONYMOUS_EDIT"],
    "pipeline_version": "0.1.0",
    "processed_at": "2026-09-28T10:00:20Z",
}


def activity_payload(rows=None):
    return {
        "data": [dict(ACTIVITY_ROW)] if rows is None else rows,
        "generated_at": "2026-09-28T10:02:00Z",
        "source": "cassandra",
        "pipeline_mode": "REPLAY",
        "provisional": True,
    }


def trends_payload(rows=None):
    data = [dict(TREND_ROW)] if rows is None else rows
    return {
        "data": data,
        "window_start": "2026-09-28T10:00:00Z" if data else None,
        "window_end": "2026-09-28T10:05:00Z" if data else None,
        "generated_at": "2026-09-28T10:02:00Z",
        "source": "cassandra",
        "pipeline_mode": "REPLAY",
        "provisional": True,
    }


def suspicious_payload(rows=None):
    return {
        "data": [dict(SUSPICIOUS_ROW)] if rows is None else rows,
        "generated_at": "2026-09-28T10:02:00Z",
        "source": "cassandra",
        "pipeline_mode": "REPLAY",
        "provisional": True,
        "disclaimer": DISCLAIMER_TEXT,
    }


def event_payload(row=None):
    return {
        "data": dict(EVENT_DETAIL_ROW) if row is None else row,
        "generated_at": "2026-09-28T10:02:00Z",
        "source": "cassandra",
        "pipeline_mode": "REPLAY",
    }


def client_for(handler, timeout=5.0):
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
        "implementation_status": "activity_trends_suspicious_events",
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


def test_trends_queries_and_validates_contract():
    requests = []

    def serve(request):
        requests.append(request)
        return httpx.Response(200, json=trends_payload())

    result = client_for(serve).get_trends("enwiki", limit=10)

    assert result.state == "ok"
    assert result.payload["data"][0]["trend_score"] == 0.85
    assert requests[0].url.path == "/api/v1/trends"
    assert dict(requests[0].url.params) == {"wiki": "enwiki", "limit": "10"}


def test_empty_trends_with_null_windows_returns_empty_state():
    result = client_for(lambda _: httpx.Response(200, json=trends_payload([]))).get_trends(
        "enwiki"
    )

    assert result.state == "empty"
    assert result.payload["window_start"] is None
    assert result.payload["window_end"] is None


def test_suspicious_edits_queries_with_filters():
    requests = []

    def serve(request):
        requests.append(request)
        return httpx.Response(200, json=suspicious_payload())

    result = client_for(serve).get_suspicious_edits(
        "enwiki", minutes=10, min_score=30, limit=50
    )

    assert result.state == "ok"
    assert result.payload["data"][0]["risk_score"] == 60
    assert requests[0].url.path == "/api/v1/suspicious-edits"
    assert dict(requests[0].url.params) == {
        "wiki": "enwiki",
        "minutes": "10",
        "min_score": "30",
        "limit": "50",
    }


def test_event_detail_fetches_by_id_and_handles_not_found():
    ok_result = client_for(
        lambda _: httpx.Response(200, json=event_payload())
    ).get_event("evt-123")
    assert ok_result.state == "ok"
    assert ok_result.payload["data"]["revision_new"] == 999002

    missing_result = client_for(
        lambda _: httpx.Response(
            404,
            json={"detail": {"code": "EVENT_NOT_FOUND", "message": "No event with this event_id"}},
        )
    ).get_event("missing-id")
    assert missing_result.state == "error"
    assert missing_result.status_code == 404
    assert missing_result.error_code == "EVENT_NOT_FOUND"


def test_capacity_exceeded_returns_clear_error_state():
    result = client_for(
        lambda _: httpx.Response(
            503,
            json={"detail": {"code": "CAPACITY_EXCEEDED", "message": "Partition exceeds 5000 rows"}},
        )
    ).get_trends("enwiki")

    assert result.state == "error"
    assert result.status_code == 503
    assert result.error_code == "CAPACITY_EXCEEDED"
    assert "5.000" in result.message


def test_invalid_query_detail_is_parsed_into_error_message():
    result = client_for(
        lambda _: httpx.Response(
            422,
            json={
                "detail": {
                    "code": "INVALID_QUERY",
                    "message": "wiki must be in WIKI_ALLOWLIST",
                    "fields": [{"name": "wiki", "message": "wiki must be in WIKI_ALLOWLIST"}],
                }
            },
        )
    ).get_trends("frwiki")

    assert result.state == "error"
    assert result.status_code == 422
    assert result.error_code == "INVALID_QUERY"
    assert "WIKI_ALLOWLIST" in result.message


@pytest.mark.parametrize(
    ("method", "arguments", "path"),
    [
        ("get_trends", ("viwiki",), "/api/v1/trends"),
        ("get_suspicious_edits", ("viwiki",), "/api/v1/suspicious-edits"),
        ("get_event", ("abc-123",), "/api/v1/events/abc-123"),
    ],
)
def test_http501_fallback_still_maps_to_not_implemented(method, arguments, path):
    detail = {"code": "NOT_IMPLEMENTED", "owner": "Nhân", "planned_week": 2}
    requests = []

    def serve(request):
        requests.append(request)
        return httpx.Response(501, json={"detail": detail})

    result = getattr(client_for(serve), method)(*arguments)

    assert result.state == "not_implemented"
    assert result.status_code == 501
    assert result.payload["detail"] == detail
    assert requests[0].url.path == path


def test_privacy_guard_rejects_leaked_user_hash_or_comment():
    leaked_suspicious = suspicious_payload([{**SUSPICIOUS_ROW, "user_hash": "abc"}])
    res1 = client_for(lambda _: httpx.Response(200, json=leaked_suspicious)).get_suspicious_edits(
        "enwiki"
    )
    assert res1.state == "error"

    leaked_event = event_payload({**EVENT_DETAIL_ROW, "comment": "secret edit summary"})
    res2 = client_for(lambda _: httpx.Response(200, json=leaked_event)).get_event("evt-123")
    assert res2.state == "error"


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
