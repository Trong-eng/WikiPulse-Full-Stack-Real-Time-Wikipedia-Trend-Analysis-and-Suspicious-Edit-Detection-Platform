# Dashboard Streamlit — Mạnh

Module giao diện trực quan hóa của nền tảng WikiPulse, xây dựng trên Streamlit.

## Tổng quan và cấu trúc

Dashboard cung cấp 4 trang đọc dữ liệu thật từ FastAPI/Cassandra:
- **Overview**: Hoạt động tổng quan theo từng wiki trong cửa sổ 1 phút (`event_count`, `edit_count`, `new_page_count`, `anonymous_edit_count`, `bot_edit_count`) và biểu đồ phân bố theo cửa sổ thời gian UTC (`GET /api/v1/activity`).
- **Trending**: Bảng xếp hạng các trang tăng hoạt động nổi bật trong cửa sổ 5 phút trượt 1 phút (`trend_score`, `edit_count`, `unique_editors`, `abs_byte_delta`), kèm link mở bài viết Wikipedia thật (`GET /api/v1/trends`).
- **Suspicious Edits**: Danh sách chỉnh sửa cần ưu tiên xem xét theo điểm rủi ro (`LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`), bộ lọc theo phút/điểm tối thiểu/bot edits, xem chi tiết sự kiện (`GET /api/v1/suspicious-edits` và `GET /api/v1/events/{event_id}`), luôn kèm câu disclaimer không kết luận phá hoại.
- **System Status**: Kiểm tra sức khỏe hệ thống từ `GET /health`, bao gồm readiness của API và Cassandra.

### Cấu trúc mã nguồn

```text
dashboard/
├── app.py                   # Entrypoint: cấu hình sidebar, router, auto-refresh 15s
├── api_client.py            # Client HTTP kết nối FastAPI qua httpx, chuẩn hóa state và lỗi v0.2
├── views/
│   ├── overview.py          # Render trang Overview (metrics + bar chart UTC)
│   ├── trending.py          # Render trang Trending (Top-N + link Wikipedia)
│   ├── suspicious_edits.py  # Render trang Suspicious Edits (filters + event detail)
│   ├── system_status.py     # Render trang System Status (readiness API/Cassandra)
│   └── future.py            # Helper dự phòng cho endpoint chưa triển khai (501)
├── tests/
│   ├── test_api_client.py   # Test client, contract v0.2, privacy guard, handling lỗi 404/422/503
│   └── test_app.py          # Streamlit AppTest kiểm thử luồng giao diện 4 trang
├── Dockerfile               # Container image cho Streamlit service
└── requirements.txt         # streamlit, httpx
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
```powershell
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

Bộ test sử dụng `streamlit.testing.v1.AppTest` để kiểm tra logic render UI, bộ lọc, xử lý lỗi và phản hồi API mock mà không cần chạy cụm dịch vụ thật:

```powershell
# Chạy toàn bộ test của dashboard:
.venv\Scripts\python -m pytest dashboard/tests -q
```

## Giới hạn và tuân thủ

- **Privacy**: Không hiển thị IP, username thô hay `user_hash` / `comment` trên bất kỳ màn hình nào; `APIClient` từ chối render nếu phát hiện rò rỉ trường nhạy cảm.
- **Disclaimer**: Điểm rủi ro chỉ dùng để ưu tiên xem xét, không kết luận phá hoại.
- **Provisional**: Số liệu phục vụ từ Cassandra được gắn nhãn tạm tính và tự làm mới định kỳ.
