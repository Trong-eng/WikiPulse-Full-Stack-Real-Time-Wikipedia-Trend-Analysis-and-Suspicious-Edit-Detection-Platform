from datetime import datetime
from urllib.parse import quote

import streamlit as st

from dashboard.api_client import APIClient


def _utc_label(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def _wikipedia_url(wiki: str, page_title: str | None) -> str | None:
    if not page_title:
        return None
    lang = wiki[:-4] if wiki.endswith("wiki") and len(wiki) > 4 else "en"
    slug = quote(page_title.replace(" ", "_"), safe=":/_")
    return f"https://{lang}.wikipedia.org/wiki/{slug}"


def render(client: APIClient, wiki: str):
    st.title("Trending")
    st.write("Các trang tăng hoạt động nổi bật trong cửa sổ 5 phút (trượt 1 phút), đọc từ API.")

    limit = st.selectbox(
        "Số trang hiển thị (Top-N)",
        [10, 20, 50, 100],
        index=1,
        key=f"trends_limit_{wiki}",
    )

    result = client.get_trends(wiki, limit=limit)
    if result.state not in {"ok", "empty"}:
        st.error(result.message)
        if result.error_code == "CAPACITY_EXCEEDED":
            st.caption("Vượt quá giới hạn 5.000 dòng cho partition; hãy thu hẹp bộ lọc.")
        else:
            st.caption("Chưa thể đọc dữ liệu xu hướng. Xem System Status để kiểm tra API và Cassandra.")
        return

    payload = result.payload
    status = "tạm tính" if payload["provisional"] else "đã chốt"
    st.caption(
        f"Mode: {payload['pipeline_mode']} · Trạng thái: {status} · Wiki: {wiki} · "
        f"Nguồn: {payload['source']}"
    )
    st.caption(f"Phản hồi API lúc: {_utc_label(payload['generated_at'])}")

    window_start = payload.get("window_start")
    window_end = payload.get("window_end")
    if window_start and window_end:
        st.caption(
            f"Cửa sổ 5 phút: {_utc_label(window_start)} → {_utc_label(window_end)} · "
            "Cửa sổ mới nhất có thể chưa đủ 5 phút dữ liệu và vẫn đang tăng."
        )

    rows = payload["data"]
    if not rows:
        st.info(
            f"Chưa có dữ liệu xu hướng cho {wiki}. "
            "Chạy REPLAY hoặc LIVE và đợi pipeline ghi cửa sổ 5 phút vào Cassandra."
        )
        return

    table_rows = [
        {
            "Hạng": idx,
            "Trang": row.get("page_title") or row["page_key"],
            "Bài viết": _wikipedia_url(wiki, row.get("page_title")),
            "Điểm xu hướng": round(float(row["trend_score"]), 4),
            "Chỉnh sửa": row["edit_count"],
            "Biên tập viên": row["unique_editors"],
            "Tổng |byte delta|": row["abs_byte_delta"],
            "Namespace": row.get("namespace"),
        }
        for idx, row in enumerate(rows, start=1)
    ]

    st.dataframe(
        table_rows,
        column_config={
            "Bài viết": st.column_config.LinkColumn("Liên kết", display_text="Mở Wikipedia"),
            "Điểm xu hướng": st.column_config.NumberColumn("Điểm xu hướng", format="%.4f"),
        },
        hide_index=True,
        use_container_width=True,
    )
