import streamlit as st

from dashboard.api_client import APIClient
from dashboard.views.future import render_status


def render(client: APIClient, wiki: str):
    st.title("Suspicious Edits")
    st.write("Tín hiệu ưu tiên xem xét chỉnh sửa; không kết luận hành vi phá hoại.")
    st.info(
        "Chưa triển khai · Tuần 2. "
        "Owner: Linh — tín hiệu/risk; Nhân — API; Mạnh — dashboard/QA."
    )
    st.caption(f"Wiki đang chọn: {wiki} · Contract: GET /api/v1/suspicious-edits")
    render_status(client.get_suspicious_edits(wiki))
