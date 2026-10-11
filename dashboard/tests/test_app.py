"""Exercise the actual Streamlit UI with only the network boundary replaced."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

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


@pytest.fixture
def server(monkeypatch):
    state = {
        "rows": [dict(ROW)],
        "activity_status": 200,
        "health_status": 200,
        "health": {
            "status": "ok",
            "source": "cassandra",
            "pipeline_mode": "REPLAY",
            "implementation_status": "activity_only",
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
        if request.url.path in {"/api/v1/trends", "/api/v1/suspicious-edits"}:
            return httpx.Response(
                501,
                json={
                    "detail": {
                        "code": "NOT_IMPLEMENTED",
                        "owner": "Nhân",
                        "planned_week": 2,
                    }
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
    assert len(app.get("arrow_vega_lite_chart")) == 1
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


@pytest.mark.parametrize(
    ("page", "endpoint"),
    [
        ("Trending", "/api/v1/trends"),
        ("Suspicious Edits", "/api/v1/suspicious-edits"),
    ],
)
def test_future_pages_show_owner_week_and_expected_http501(server, page, endpoint):
    app = run_app()
    app.radio(key="page").set_value(page).run()

    assert not app.exception
    assert not app.metric
    text = all_text(app.info) + all_text(app.caption)
    assert "chưa triển khai" in text.lower()
    assert "Tuần 2" in text
    assert "Mạnh" in text
    assert "Nhân" in text
    assert "Linh" in text
    assert "HTTP 501" in text
    assert server["requests"][-1].url.path == endpoint


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
