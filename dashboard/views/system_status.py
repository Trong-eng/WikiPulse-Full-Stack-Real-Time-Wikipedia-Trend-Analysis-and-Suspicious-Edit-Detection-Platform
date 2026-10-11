import os
from datetime import datetime, timezone

import streamlit as st

from dashboard.api_client import APIClient


def render(client: APIClient, wiki: str):
    st.title("System Status")
    st.write("Readiness thực tế từ GET /health của API, bao gồm dependency Cassandra.")
    result = client.get_health()
    st.caption(f"Kiểm tra lúc: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S UTC}")
    st.caption(f"API: {client.base_url} · Trạng thái hệ thống áp dụng cho toàn dịch vụ.")
    if result.status_code is None:
        st.error(result.message)
        st.caption("Chưa có phản hồi health; chưa xác minh được readiness Cassandra.")
    else:
        payload = result.payload or {}
        dependencies = payload.get("dependencies", {})
        cassandra = (
            dependencies.get("cassandra", "chưa xác minh")
            if isinstance(dependencies, dict)
            else "chưa xác minh"
        )
        api_column, cassandra_column = st.columns(2)
        api_column.metric("API · readiness", f"HTTP {result.status_code}")
        cassandra_column.metric("Cassandra", str(cassandra))
        if result.state == "ok" and payload.get("status") == "ok" and cassandra == "ready":
            st.success("API và Cassandra đã báo sẵn sàng.")
        else:
            st.error(result.message or "API chưa báo readiness hợp lệ.")
        st.caption(
            f"Mode: {payload.get('pipeline_mode', 'chưa xác minh')} · "
            f"Implementation: {payload.get('implementation_status', 'chưa xác minh')}"
        )
        with st.expander("Phản hồi /health"):
            st.json(payload)

    st.subheader("Cấu hình Kafka")
    st.code(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"), language=None)
    st.info("Kafka: chỉ hiển thị cấu hình (configured); dashboard chưa kiểm tra kết nối Kafka.")
    st.caption("Tuần 2 · Mạnh/Trọng: mở rộng health và thông tin vận hành theo contract.")
