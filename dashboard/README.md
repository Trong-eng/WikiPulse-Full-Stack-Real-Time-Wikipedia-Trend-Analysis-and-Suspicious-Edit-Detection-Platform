# Dashboard Streamlit — Mạnh, tuần 1

Module giao diện trực quan hóa của nền tảng WikiPulse, xây dựng trên Streamlit.

## Tổng quan và cấu trúc

Dashboard cung cấp giao diện theo dõi 4 trang:
- **Overview**: Hoạt động tổng quan theo từng wiki trong cửa sổ 1 phút (`event_count`, `edit_count`, `new_page_count`, `anonymous_edit_count`, `bot_edit_count`) và biểu đồ phân bố theo cửa sổ thời gian UTC. Dữ liệu đọc từ FastAPI endpoint `GET /api/v1/activity`.
- **Trending**: Theo dõi trang có đột biến hoạt động (kế hoạch Tuần 2; CP0 phản hồi HTTP 501 `NOT_IMPLEMENTED`).
- **Suspicious Edits**: Tín hiệu cảnh báo ưu tiên xem xét chỉnh sửa đáng ngờ (kế hoạch Tuần 2; CP0 phản hồi HTTP 501 `NOT_IMPLEMENTED`).
- **System Status**: Kiểm tra sức khỏe hệ thống từ `GET /health`, bao gồm readiness của API và Cassandra.

### Cấu trúc mã nguồn

```text
dashboard/
├── app.py                # Entrypoint: cấu hình sidebar, router, auto-refresh 15s
├── api_client.py         # Client HTTP kết nối FastAPI qua httpx, chuẩn hóa state
├── views/
│   ├── overview.py       # Render trang Overview (metrics + bar chart)
│   ├── trending.py       # Render trang Trending (trạng thái 501 Tuần 2)
│   ├── suspicious_edits.py # Render trang Suspicious Edits (trạng thái 501 Tuần 2)
│   ├── system_status.py  # Render trang System Status (readiness API/Cassandra)
│   └── future.py         # Helper hiển thị trạng thái API chưa triển khai
├── tests/
│   ├── test_api_client.py # Test client, timeout, handling HTTP 501/503
│   └── test_app.py        # Streamlit AppTest kiểm thử luồng giao diện
├── Dockerfile            # Container image cho Streamlit service
└── requirements.txt      # streamlit, httpx
```

## Cách chạy

### 1. Chạy trong Docker Compose (khuyến nghị cho demo)

Dashboard khởi động cùng stack chính qua Docker Compose:

```bash
docker compose up -d dashboard
```

Mở trình duyệt tại: `http://localhost:8501`.

### 2. Chạy local từ máy host

Yêu cầu đã kích hoạt virtualenv `.venv` và cài đặt dependencies:

```bash
# Từ thư mục gốc của repository:
streamlit run dashboard/app.py
```

Khi chạy local, cấu hình URL trỏ tới cổng host của API:
```bash
# PowerShell:
$env:DASHBOARD_API_URL="http://localhost:18000"
streamlit run dashboard/app.py
```

## Biến môi trường

| Biến | Mặc định | Mô tả |
|---|---|---|
| `DASHBOARD_API_URL` | `http://localhost:18000` (local) / `http://api:8000` (container) | Base URL của dịch vụ FastAPI |
| `WIKI_ALLOWLIST` | `enwiki,viwiki` | Danh sách wiki hiển thị ở menu chọn |
| `DASHBOARD_HOST_PORT` | `8501` | Cổng map ra máy host |

## Cơ chế làm mới dữ liệu

- Dashboard tự động kích hoạt làm mới giao diện mỗi 15 giây thông qua `@st.fragment(run_every="15s")`.
- Người dùng có thể nhấn nút **"Làm mới dữ liệu"** tại sidebar để cập nhật tức thì.

## Kiểm thử

Bộ test sử dụng `streamlit.testing.v1.AppTest` để kiểm tra logic render UI và xử lý phản hồi API mock mà không cần chạy cụm dịch vụ thật:

```bash
# Chạy toàn bộ test của dashboard:
.venv\Scripts\python -m pytest dashboard/tests -q
```

## Giới hạn và tuân thủ

- **Privacy**: Không hiển thị IP hoặc username thô của người dùng Wikipedia trên bất kỳ màn hình nào.
- **CP0 Scope**: Chỉ trang Overview và System Status có dữ liệu thực tế. Các trang Trending và Suspicious Edits hiển thị rõ ràng thông tin HTTP 501 và phụ trách module/tuần bàn giao.
