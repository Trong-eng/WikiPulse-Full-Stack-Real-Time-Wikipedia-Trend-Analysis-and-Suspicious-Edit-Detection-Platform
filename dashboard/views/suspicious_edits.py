from datetime import datetime

import streamlit as st

from dashboard.api_client import DISCLAIMER_TEXT, APIClient

REASON_LABELS = {
    "LARGE_DELETION": "Xóa nhiều nội dung",
    "REVERT_PATTERN": "Dấu hiệu hoàn tác",
    "ANONYMOUS_EDIT": "Chỉnh sửa ẩn danh",
}


def _utc_label(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def _format_reasons(reasons: list[str]) -> str:
    return ", ".join(REASON_LABELS.get(r, r) for r in reasons) if reasons else "Không có"


def render(client: APIClient, wiki: str):
    st.title("Suspicious Edits")
    st.write("Tín hiệu ưu tiên xem xét chỉnh sửa theo điểm rủi ro.")

    col_min, col_score, col_limit = st.columns(3)
    with col_min:
        minutes = st.slider(
            "Khoảng thời gian (phút)",
            min_value=1,
            max_value=15,
            value=5,
            key=f"suspicious_minutes_{wiki}",
        )
    with col_score:
        min_score = st.slider(
            "Điểm rủi ro tối thiểu",
            min_value=0,
            max_value=100,
            value=0,
            step=10,
            key=f"suspicious_min_score_{wiki}",
        )
    with col_limit:
        limit = st.selectbox(
            "Số dòng tối đa",
            [10, 20, 50, 100],
            index=1,
            key=f"suspicious_limit_{wiki}",
        )

    include_bots = st.checkbox(
        "Hiển thị chỉnh sửa từ bot",
        value=True,
        key=f"suspicious_include_bots_{wiki}",
    )

    result = client.get_suspicious_edits(
        wiki, minutes=minutes, min_score=min_score, limit=limit
    )
    if result.state not in {"ok", "empty"}:
        st.error(result.message)
        if result.error_code == "CAPACITY_EXCEEDED":
            st.caption("Vượt quá giới hạn 5.000 dòng; hãy giảm số phút hoặc thu hẹp bộ lọc.")
        else:
            st.caption(
                "Chưa thể đọc danh sách chỉnh sửa đáng ngờ. Xem System Status để kiểm tra API."
            )
        return

    payload = result.payload
    st.warning(payload.get("disclaimer") or DISCLAIMER_TEXT)

    status = "tạm tính" if payload["provisional"] else "đã chốt"
    st.caption(
        f"Mode: {payload['pipeline_mode']} · Trạng thái: {status} · Wiki: {wiki} · "
        f"Nguồn: {payload['source']} · Cửa sổ: {minutes} phút gần nhất"
    )
    st.caption(f"Phản hồi API lúc: {_utc_label(payload['generated_at'])}")

    rows = payload["data"]
    if not include_bots:
        rows = [row for row in rows if not row.get("is_bot")]

    if not rows:
        st.info(
            f"Không có chỉnh sửa đáng ngờ phù hợp bộ lọc cho {wiki} "
            f"(min_score ≥ {min_score}, {minutes} phút)."
        )
        return

    table_rows = [
        {
            "Thời điểm (UTC)": _utc_label(row["event_time"]),
            "Trang": row.get("page_title") or row["page_key"],
            "Điểm rủi ro": row["risk_score"],
            "Lý do": _format_reasons(row.get("risk_reasons", [])),
            "Byte delta": row.get("byte_delta"),
            "Ẩn danh": "Có" if row.get("is_anonymous") else "Không",
            "Bot": "Có" if row.get("is_bot") else "Không",
            "Revision mới": row.get("revision_new"),
            "Event ID": row["event_id"],
        }
        for row in rows
    ]

    st.dataframe(table_rows, hide_index=True, use_container_width=True)

    st.subheader("Chi tiết sự kiện")
    event_options = [row["event_id"] for row in rows]
    event_labels = {
        row["event_id"]: (
            f"{row.get('page_title') or row['page_key']} · "
            f"Điểm {row['risk_score']} · {_utc_label(row['event_time'])}"
        )
        for row in rows
    }
    selected_event_id = st.selectbox(
        "Chọn sự kiện để xem chi tiết",
        event_options,
        format_func=lambda eid: event_labels[eid],
        key=f"suspicious_event_select_{wiki}",
    )

    if st.button("Xem chi tiết sự kiện", key=f"load_event_detail_{wiki}"):
        detail_result = client.get_event(selected_event_id)
        if detail_result.state != "ok":
            st.error(detail_result.message)
        else:
            event_data = detail_result.payload["data"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Điểm rủi ro", event_data["risk_score"])
            c2.metric("Byte delta", event_data.get("byte_delta") if event_data.get("byte_delta") is not None else "N/A")
            c3.metric("Revision mới", event_data.get("revision_new") if event_data.get("revision_new") is not None else "N/A")
            c4.metric("Loại sự kiện", event_data["event_type"])
            st.caption(
                f"Event ID: `{event_data['event_id']}` · "
                f"Trang: {event_data.get('page_title') or event_data['page_key']} · "
                f"Lý do: {_format_reasons(event_data.get('risk_reasons', []))}"
            )
            st.caption(
                f"Revision cũ: {event_data.get('revision_old')} → "
                f"Revision mới: {event_data.get('revision_new')} · "
                f"Độ dài cũ: {event_data.get('length_old')} → "
                f"Độ dài mới: {event_data.get('length_new')} · "
                f"Minor: {'Có' if event_data.get('is_minor') else 'Không'}"
            )
