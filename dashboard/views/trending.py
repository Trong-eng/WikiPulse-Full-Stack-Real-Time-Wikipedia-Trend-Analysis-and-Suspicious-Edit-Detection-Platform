import streamlit as st

from dashboard.api_client import APIClient
from dashboard.views.future import render_status


def render(client: APIClient, wiki: str):
    st.title("Trending")
    st.write("Các trang đang tăng hoạt động theo cửa sổ thời gian.")
    st.info(
        "Chưa triển khai · Tuần 2. "
        "Owner: Linh — analytics; Nhân — API; Mạnh — dashboard/QA."
    )
    st.caption(f"Wiki đang chọn: {wiki} · Contract: GET /api/v1/trends")
    render_status(client.get_trends(wiki))
