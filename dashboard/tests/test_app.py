"""Exercise the actual Streamlit UI with only the network boundary replaced."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.api_client import DISCLAIMER_TEXT

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
ROW = {
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

SUSPICIOUS_HUMAN_ROW = {
    "wiki": "enwiki",
    "event_id": "evt-human-1",
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

SUSPICIOUS_BOT_ROW = {
    "wiki": "enwiki",
    "event_id": "evt-bot-2",
    "bucket_start": "2026-09-28T10:00:00Z",
    "event_time": "2026-09-28T10:00:10Z",
    "page_key": "99",
    "page_title": "Bot_maintained_page",
    "revision_new": 999003,
    "byte_delta": -1200,
    "is_anonymous": False,
    "is_bot": True,
    "risk_score": 30,
    "risk_reasons": ["LARGE_DELETION"],
    "updated_at": "2026-09-28T10:00:25Z",
}

EVENT_DETAIL = {
    "event_id": "evt-human-1",
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


@pytest.fixture
def server(monkeypatch):
    state = {
        "rows": [dict(ROW)],
        "activity_status": 200,
        "trends_rows": [dict(TREND_ROW)],
        "trends_status": 200,
        "trends_error_detail": None,
        "suspicious_rows": [dict(SUSPICIOUS_HUMAN_ROW), dict(SUSPICIOUS_BOT_ROW)],
        "suspicious_status": 200,
        "event_detail": dict(EVENT_DETAIL),
        "event_status": 200,
        "health_status": 200,
        "health": {
            "status": "ok",
            "source": "cassandra",
            "pipeline_mode": "REPLAY",
            "implementation_status": "activity_trends_suspicious_events",
            "dependencies": {"cassandra": "ready"},
        },
        "requests": [],
        "timeout": False,
    }

    def serve(request):
        state["requests"].append(request)
        if state["timeout"]:
            raise httpx.ReadTimeout("API timed out", request=request)
        if request.url.path == "/api/v1/activity":
            if state["activity_status"] != 200:
                return httpx.Response(state["activity_status"], json={"detail": "unavailable"})
            wiki = request.url.params["wiki"]
            rows = [{**row, "wiki": wiki} for row in state["rows"]]
            return httpx.Response(
                200,
                json={
                    "data": rows,
                    "generated_at": "2026-09-28T10:02:00Z",
                    "source": "cassandra",
                    "pipeline_mode": "REPLAY",
                    "provisional": True,
                },
            )
        if request.url.path == "/health":
            return httpx.Response(state["health_status"], json=state["health"])
        if request.url.path == "/api/v1/trends":
            if state["trends_status"] != 200:
                detail = state["trends_error_detail"] or {
                    "code": "DEPENDENCY_UNAVAILABLE",
                    "message": "Cassandra unavailable",
                }
                return httpx.Response(state["trends_status"], json={"detail": detail})
            wiki = request.url.params["wiki"]
            rows = [{**row, "wiki": wiki} for row in state["trends_rows"]]
            return httpx.Response(
                200,
                json={
                    "data": rows,
                    "window_start": "2026-09-28T10:00:00Z" if rows else None,
                    "window_end": "2026-09-28T10:05:00Z" if rows else None,
                    "generated_at": "2026-09-28T10:02:00Z",
                    "source": "cassandra",
                    "pipeline_mode": "REPLAY",
                    "provisional": True,
                },
            )
        if request.url.path == "/api/v1/suspicious-edits":
            if state["suspicious_status"] != 200:
                return httpx.Response(
                    state["suspicious_status"],
                    json={"detail": {"code": "DEPENDENCY_UNAVAILABLE", "message": "Unavailable"}},
                )
            wiki = request.url.params["wiki"]
            rows = [{**row, "wiki": wiki} for row in state["suspicious_rows"]]
            return httpx.Response(
                200,
                json={
                    "data": rows,
                    "generated_at": "2026-09-28T10:02:00Z",
                    "source": "cassandra",
                    "pipeline_mode": "REPLAY",
                    "provisional": True,
                    "disclaimer": DISCLAIMER_TEXT,
                },
            )
        if request.url.path.startswith("/api/v1/events/"):
            if state["event_status"] != 200:
                return httpx.Response(
                    state["event_status"],
                    json={"detail": {"code": "EVENT_NOT_FOUND", "message": "Not found"}},
                )
            return httpx.Response(
                200,
                json={
                    "data": state["event_detail"],
                    "generated_at": "2026-09-28T10:02:00Z",
                    "source": "cassandra",
                    "pipeline_mode": "REPLAY",
                },
            )
        pytest.fail(f"Unexpected dashboard HTTP endpoint: {request.url}")

    original_client = httpx.Client
    transport = httpx.MockTransport(serve)

    def network_boundary(**kwargs):
        return original_client(**{**kwargs, "transport": transport})

    monkeypatch.setattr(httpx, "Client", network_boundary)
    monkeypatch.setenv("DASHBOARD_API_URL", "http://fixture-api:8000")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fixture-kafka:9092")
    monkeypatch.setenv("WIKI_ALLOWLIST", "enwiki,viwiki")
    return state


def run_app():
    assert APP_PATH.is_file(), "Streamlit dashboard entrypoint has not been implemented"
    # First chart imports can be slow on a cold environment; API timeout remains 5s.
    return AppTest.from_file(str(APP_PATH), default_timeout=30).run()


def all_text(elements):
    return "\n".join(element.value for element in elements)


def test_overview_renders_api_counts_and_selected_window_metadata(server):
    app = run_app()

    assert not app.exception
    assert [metric.value for metric in app.metric] == ["7", "5", "2", "3", "1"]
    captions = all_text(app.caption)
    assert "REPLAY" in captions
    assert "tạm tính" in captions.lower()
    assert "enwiki" in captions
    assert "2026-09-28 10:00:00 UTC" in captions
    assert "2026-09-28 10:01:08 UTC" in captions
    assert "tổng toàn cầu" in captions.lower()
    charts = app.get("arrow_vega_lite_chart")
    assert len(charts) == 1
    assert '"type": "nominal"' in charts[0].proto.spec
    request = server["requests"][0]
    assert request.url.host == "fixture-api"
    assert dict(request.url.params) == {"wiki": "enwiki", "limit": "5"}


def test_wiki_selector_fetches_the_chosen_wiki(server):
    app = run_app()
    app.selectbox(key="wiki").set_value("viwiki").run()

    assert not app.exception
    assert server["requests"][-1].url.params["wiki"] == "viwiki"
    assert "viwiki" in all_text(app.caption)


def test_wiki_selector_and_api_request_use_configured_allowlist(server, monkeypatch):
    monkeypatch.setenv("WIKI_ALLOWLIST", "dewiki")
    app = run_app()

    assert not app.exception
    assert app.selectbox(key="wiki").options == ["dewiki"]
    assert app.selectbox(key="wiki").value == "dewiki"
    assert server["requests"][-1].url.params["wiki"] == "dewiki"
    assert "dewiki" in all_text(app.caption)


def test_local_api_default_uses_compose_published_port(server, monkeypatch):
    monkeypatch.delenv("DASHBOARD_API_URL")
    app = run_app()

    assert not app.exception
    request = server["requests"][0]
    assert request.url.host == "localhost"
    assert request.url.port == 18000


def test_window_selector_changes_metrics_to_that_window(server):
    server["rows"].append(
        {
            **ROW,
            "window_start": "2026-09-28T09:59:00Z",
            "window_end": "2026-09-28T10:00:00Z",
            "event_count": 4,
            "edit_count": 3,
            "new_page_count": 1,
            "anonymous_edit_count": 1,
            "bot_edit_count": 0,
        }
    )
    app = run_app()
    app.selectbox(key="activity_window_enwiki").set_value("2026-09-28T09:59:00Z").run()

    assert not app.exception
    assert [metric.value for metric in app.metric] == ["4", "3", "1", "1", "0"]


def test_manual_refresh_fetches_new_api_values(server):
    app = run_app()
    server["rows"][0]["event_count"] = 11
    app.button(key="refresh").click().run()

    assert not app.exception
    assert app.metric[0].value == "11"
    assert len(server["requests"]) == 2


def test_empty_dataset_shows_no_fabricated_metrics(server):
    server["rows"] = []
    app = run_app()

    assert not app.exception
    assert not app.metric
    assert "chưa có dữ liệu" in all_text(app.info).lower()
    assert "REPLAY" in all_text(app.caption)


@pytest.mark.parametrize("failure", ["http503", "timeout"])
def test_api_outage_shows_an_error_without_counts(server, failure):
    if failure == "timeout":
        server["timeout"] = True
    else:
        server["activity_status"] = 503
    app = run_app()

    assert not app.exception
    assert not app.metric
    assert app.error


def test_trending_renders_table_links_and_provisional_metadata(server):
    app = run_app()
    app.radio(key="page").set_value("Trending").run()

    assert not app.exception
    assert len(app.dataframe) == 1
    df = app.dataframe[0].value
    assert df.iloc[0]["Trang"] == "Python (programming language)"
    assert df.iloc[0]["Bài viết"] == "https://en.wikipedia.org/wiki/Python_%28programming_language%29"
    assert df.iloc[0]["Chỉnh sửa"] == 12
    captions = all_text(app.caption)
    assert "tạm tính" in captions.lower()
    assert "2026-09-28 10:00:00 UTC" in captions
    assert server["requests"][-1].url.path == "/api/v1/trends"


def test_trending_handles_empty_and_capacity_exceeded(server):
    server["trends_rows"] = []
    app = run_app()
    app.radio(key="page").set_value("Trending").run()
    assert not app.exception
    assert not app.dataframe
    assert "chưa có dữ liệu xu hướng" in all_text(app.info).lower()

    server["trends_status"] = 503
    server["trends_error_detail"] = {"code": "CAPACITY_EXCEEDED", "message": "Over 5000 rows"}
    app.button(key="refresh").click().run()
    assert not app.exception
    assert app.error
    assert "5.000" in all_text(app.error)


def test_suspicious_edits_renders_disclaimer_bot_filter_and_event_detail(server):
    app = run_app()
    app.radio(key="page").set_value("Suspicious Edits").run()

    assert not app.exception
    assert DISCLAIMER_TEXT in all_text(app.warning)
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 2

    app.checkbox(key="suspicious_include_bots_enwiki").set_value(False).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["Event ID"] == "evt-human-1"

    app.button(key="load_event_detail_enwiki").click().run()
    assert not app.exception
    assert server["requests"][-1].url.path == "/api/v1/events/evt-human-1"
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Điểm rủi ro"] == "60"
    assert metrics["Byte delta"] == "-1500"
    assert metrics["Revision mới"] == "999002"


def test_suspicious_edits_handles_empty_and_outage(server):
    server["suspicious_rows"] = []
    app = run_app()
    app.radio(key="page").set_value("Suspicious Edits").run()

    assert not app.exception
    assert not app.dataframe
    assert "không có chỉnh sửa đáng ngờ" in all_text(app.info).lower()

    server["suspicious_status"] = 503
    app.button(key="refresh").click().run()
    assert not app.exception
    assert app.error


def test_system_status_uses_actual_cassandra_readiness_and_only_kafka_configuration(server):
    server["health_status"] = 503
    server["health"] = {
        **server["health"],
        "status": "unavailable",
        "dependencies": {"cassandra": "unavailable"},
    }
    app = run_app()
    app.radio(key="page").set_value("System Status").run()

    assert not app.exception
    assert server["requests"][-1].url.path == "/health"
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["API · readiness"] == "HTTP 503"
    assert metrics["Cassandra"] == "unavailable"
    assert "fixture-kafka:9092" in all_text(app.code)
    assert "chưa kiểm tra kết nối" in all_text(app.info).lower()
    assert app.error
