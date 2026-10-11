import streamlit as st

from dashboard.api_client import APIResult


def render_status(result: APIResult):
    if result.state == "not_implemented":
        st.caption("API HTTP 501 · NOT_IMPLEMENTED · Phản hồi dự kiến trong CP0.")
        detail = result.payload.get("detail", result.payload)
        if isinstance(detail, dict):
            owner = detail.get("owner", "chưa cung cấp")
            week = detail.get("planned_week", detail.get("week", "chưa cung cấp"))
            st.caption(f"Bàn giao API: {owner} · Tuần {week}")
    elif result.state in {"error", "unavailable"}:
        st.error(result.message)
        st.caption("Chưa xác minh được phản hồi HTTP 501 từ API.")
    else:
        st.warning("API đã phản hồi dữ liệu; trang hiển thị nghiệp vụ dành cho Tuần 2.")
