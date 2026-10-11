"""Exercise the real Streamlit dashboard and its live API inside the dashboard image."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def inspect_dashboard() -> dict:
    expected = json.loads((ROOT / "tests/fixtures/expected_activity.json").read_text())
    window = datetime.fromisoformat(expected["window_start"])
    start_label = window.strftime("%Y-%m-%d %H:%M:%S UTC")
    end_label = (window + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=30).run()
    assert not app.exception, app.exception
    assert not app.error, app.error
    observed = {}
    fields = {
        "Sự kiện": "event_count",
        "Chỉnh sửa": "edit_count",
        "Trang mới": "new_page_count",
        "Chỉnh sửa ẩn danh": "anonymous_edit_count",
        "Chỉnh sửa từ bot": "bot_edit_count",
    }
    for wanted in expected["rows"]:
        wiki = wanted["wiki"]
        app.selectbox(key="wiki").set_value(wiki).run()
        assert not app.exception, app.exception
        assert not app.error, app.error
        app.selectbox(key=f"activity_window_{wiki}").set_value(expected["window_start"]).run()
        assert not app.exception, app.exception
        assert not app.error, app.error
        selected = app.selectbox(key=f"activity_window_{wiki}").value
        assert datetime.fromisoformat(selected.replace("Z", "+00:00")) == window, selected
        metrics = {metric.label: metric.value for metric in app.metric}
        assert metrics == {label: str(wanted[field]) for label, field in fields.items()}, metrics
        captions = "\n".join(caption.value for caption in app.caption)
        assert f"Mode: REPLAY · Trạng thái: tạm tính · Wiki: {wiki} · Nguồn: cassandra" in captions
        metadata = next(caption.value for caption in app.caption if caption.value.startswith("Cửa sổ:"))
        assert re.fullmatch(
            rf"Cửa sổ: {re.escape(start_label)} → {re.escape(end_label)} · "
            r"updated_at: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC",
            metadata,
        ), metadata
        observed[wiki] = {"window_start": selected, "metrics": metrics, "metadata": metadata}

    app.radio(key="page").set_value("System Status").run()
    assert not app.exception, app.exception
    assert not app.error, app.error
    readiness = {metric.label: metric.value for metric in app.metric}
    assert readiness == {"API · readiness": "HTTP 200", "Cassandra": "ready"}, readiness
    assert app.success, "System Status did not confirm API/Cassandra readiness"
    return {"status": "passed", "overview": observed, "readiness": readiness}


if __name__ == "__main__":
    print(json.dumps(inspect_dashboard(), ensure_ascii=False, indent=2))
