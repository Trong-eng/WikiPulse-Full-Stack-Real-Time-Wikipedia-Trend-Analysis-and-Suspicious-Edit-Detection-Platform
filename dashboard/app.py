"""Run from the repository root with streamlit run dashboard/app.py."""

import os
import sys
from pathlib import Path

import streamlit as st
from wikipulse_core.config import Settings

# Streamlit adds the script directory to sys.path; imports also need the repo root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from dashboard.api_client import APIClient  # noqa: E402
from dashboard.views import overview, suspicious_edits, system_status, trending  # noqa: E402

st.set_page_config(page_title="WikiPulse", page_icon="◉", layout="wide")
settings = Settings.from_env()

with st.sidebar:
    st.title("◉ WikiPulse")
    st.caption("Hoạt động Wikipedia · Demo học thuật")
    page = st.radio(
        "Trang",
        ["Overview", "Trending", "Suspicious Edits", "System Status"],
        key="page",
    )
    wiki = st.selectbox("Wikipedia", settings.wiki_allowlist, key="wiki")
    st.button("Làm mới dữ liệu", key="refresh", use_container_width=True)
    st.caption("Tự làm mới mỗi 15 giây khi trang đang mở.")
    st.divider()
    st.caption("CP0 · Tuần 1\n\nOverview: dữ liệu activity từ API/Cassandra.")

client = APIClient(os.getenv("DASHBOARD_API_URL", "http://localhost:18000"))
renderers = {
    "Overview": overview.render,
    "Trending": trending.render,
    "Suspicious Edits": suspicious_edits.render,
    "System Status": system_status.render,
}


@st.fragment(run_every="15s")
def render_current_page():
    renderers[page](client, wiki)


render_current_page()
