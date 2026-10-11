from datetime import datetime

import streamlit as st

from dashboard.api_client import APIClient


def utc_label(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def render(client: APIClient, wiki: str):
    st.title("Overview")
    st.write("Hoạt động theo wiki trong cửa sổ 1 phút, lấy trực tiếp từ API.")
    result = client.get_activity(wiki, limit=5)
    if result.state not in {"ok", "empty"}:
        st.error(result.message)
        st.caption("Chưa thể đọc activity. Xem System Status để kiểm tra API và Cassandra.")
        return

    payload = result.payload
    status = "tạm tính" if payload["provisional"] else "đã chốt"
    st.caption(
        f"Mode: {payload['pipeline_mode']} · Trạng thái: {status} · Wiki: {wiki} · "
        f"Nguồn: {payload['source']}"
    )
    st.caption(f"Phản hồi API lúc: {utc_label(payload['generated_at'])}")
    st.caption(
        "Các chỉ số chỉ áp dụng cho wiki và cửa sổ đang chọn; không phải tổng toàn cầu."
    )
    rows = payload["data"]
    if not rows:
        st.info(
            f"Chưa có dữ liệu hoạt động cho {wiki}. "
            "Chạy REPLAY và đợi pipeline ghi cửa sổ vào Cassandra."
        )
        st.caption("Cửa sổ: chưa có dữ liệu · updated_at: chưa có dữ liệu")
        return

    rows = sorted(rows, key=lambda row: row["window_start"], reverse=True)
    selected_window = st.selectbox(
        "Cửa sổ hoạt động (UTC)",
        [row["window_start"] for row in rows],
        format_func=utc_label,
        key=f"activity_window_{wiki}",
    )
    selected = next(row for row in rows if row["window_start"] == selected_window)
    st.caption(
        f"Cửa sổ: {utc_label(selected['window_start'])} → "
        f"{utc_label(selected['window_end'])} · "
        f"updated_at: {utc_label(selected['updated_at'])}"
    )

    metrics = (
        ("Sự kiện", "event_count"),
        ("Chỉnh sửa", "edit_count"),
        ("Trang mới", "new_page_count"),
        ("Chỉnh sửa ẩn danh", "anonymous_edit_count"),
        ("Chỉnh sửa từ bot", "bot_edit_count"),
    )
    for column, (label, field) in zip(st.columns(len(metrics)), metrics, strict=True):
        column.metric(label, selected[field])

    st.subheader("Số sự kiện qua các cửa sổ")
    st.caption(f"Tối đa 5 cửa sổ mới nhất có dữ liệu của {wiki}; trục thời gian UTC.")
    chart_rows = [
        {
            "Cửa sổ (UTC)": datetime.fromisoformat(row["window_start"].replace("Z", "+00:00")),
            "Số sự kiện": row["event_count"],
        }
        for row in reversed(rows)
    ]
    st.bar_chart(
        chart_rows,
        x="Cửa sổ (UTC)",
        y="Số sự kiện",
        color="#0F766E",
        use_container_width=True,
    )
