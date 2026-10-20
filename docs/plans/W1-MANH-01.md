# W1-MANH-01 — Tiếp quản 4 trang/client/Overview, chạy CP0 máy mình

Trạng thái: REVIEW · Owner: Mạnh · Reviewer: Trọng, Nhân · Liên quan: [checkpoints](../checkpoints.md)

## Mục tiêu

Tiếp quản module `dashboard`, hiểu và kiểm chứng hoạt động của 4 trang giao diện (`Overview`, `Trending`, `Suspicious Edits`, `System Status`) cùng `APIClient`. Chạy lại thành công CP0 trên môi trường Windows local, kiểm chứng toàn bộ luồng REPLAY -> Kafka -> Spark -> Cassandra -> API -> Dashboard. Tạo tài liệu `dashboard/README.md` theo quy định AGENTS.md.

## Phạm vi / Không làm

- Làm:
  - Tiếp quản mã nguồn `dashboard/app.py`, `dashboard/api_client.py`, `dashboard/views/`, `dashboard/tests/`.
  - Tạo tài liệu `dashboard/README.md` (hướng dẫn chạy, flags, giới hạn module).
  - Kiểm thử unit test & linter cho dashboard và toàn bộ suite (`pytest`, `ruff`).
  - Chạy thực tế stack CP0 trên máy local (Windows 11, Docker Desktop), kiểm tra và xác minh 4 trang giao diện.
  - Tích hợp kiểm thử luồng dữ liệu tự động giữa UI và API thực tế.
- Không làm:
  - Triển khai nghiệp vụ thực tế cho Trending, Suspicious Edits (đây là phạm vi của Tuần 2 theo kế hoạch).
  - Sửa logic xử lý dữ liệu Spark hay Cassandra (thuộc sở hữu của Linh và Nhân).

## Các bước

- [x] Tạo branch `manh/w1-manh-01-dashboard-takeover` và lập plan `docs/plans/W1-MANH-01.md`
- [x] Dựng môi trường Python local (.venv với Python 3.11) và chạy unit tests của dashboard
- [x] Soát lỗi linter với `ruff`
- [x] Viết `dashboard/README.md` mô tả cấu trúc, cách chạy, biến môi trường và giới hạn
- [x] Khởi động Docker Compose stack, chạy REPLAY và kiểm tra CP0
- [x] Xác minh 4 trang giao diện trên Streamlit dashboard và API endpoints
- [x] Cập nhật kết quả, nhật ký và chuyển checkpoint sang REVIEW

## Quyết định

- Giao diện CP0: Trang Overview hiển thị số liệu activity thực tế từ API/Cassandra. 3 trang còn lại giữ trạng thái thông báo rõ ràng (Trending/Suspicious báo 501 chờ Tuần 2; System Status hiển thị readiness của API & Cassandra).
- Môi trường: Chạy trên Windows với Python 3.11 trong `.venv`, kết nối trực tiếp với Docker Desktop.
- Do sandbox không hỗ trợ tải binary Playwright của subagent, việc kiểm tra UI được xác minh qua 2 tầng:
  1. Kiểm thử tự động Streamlit `AppTest` kết nối trực tiếp với backend thật.
  2. Streamlit Dashboard chạy thật tại `http://localhost:8501` để Mạnh kiểm tra trực quan và lưu screenshots.

## Nhật ký

- 2026-10-20 — Khởi tạo branch `manh/w1-manh-01-dashboard-takeover`, xác nhận cấu hình `.env`, lập plan W1-MANH-01.
- 2026-10-20 — Cài đặt `.venv` (Python 3.11.9), chạy test `dashboard/tests` (34 passed), toàn bộ unit test (121 passed), `ruff check .` (All checks passed).
- 2026-10-20 — Viết tài liệu `dashboard/README.md` chuẩn hóa theo AGENTS.md §4.
- 2026-10-20 — Khởi động Docker Compose stack CP0 (`kafka`, `cassandra`, `spark`, `api`, `dashboard`). Replay nạp 11 event fixture vào Kafka (`docker compose run --rm -T --no-deps replay`).
- 2026-10-20 — Xác minh kết quả trên API và Dashboard:
  - `GET /health` trả về `{"status": "ok", "dependencies": {"cassandra": "ready"}}`.
  - `GET /api/v1/activity?wiki=enwiki` trả về đúng 2 cửa sổ: window `00:00` (5 events, 5 edits, 1 anon, 1 bot) và window `00:12` (1 event).
  - `GET /api/v1/activity?wiki=viwiki` trả về window `00:00` (1 event, 1 new page).
  - Streamlit `AppTest` kiểm tra 4 trang: Overview hiển thị chuẩn 5 metrics; System Status báo HTTP 200 và Cassandra ready; Trending và Suspicious Edits hiển thị HTTP 501 Tuần 2.
- 2026-10-20 — Chuyển trạng thái plan và checkpoint sang REVIEW.

## Kết quả

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Dashboard unit & UI tests | `.venv\Scripts\python -m pytest dashboard/tests -q` | 34 passed |
| Toàn bộ unit tests | `.venv\Scripts\python -m pytest -q -m "not integration and not spark"` | 121 passed, 13 deselected |
| Lint code | `.venv\Scripts\ruff check .` | All checks passed |
| Replay fixture chạy thật | `docker compose run --rm -T --no-deps replay` | 11 events published, exit code 0 |
| API Health | `curl http://localhost:18000/health` | HTTP 200, status `ok`, Cassandra `ready` |
| API Activity enwiki | `curl "http://localhost:18000/api/v1/activity?wiki=enwiki"` | 2 cửa sổ (00:00: 5/5/0/1/1, 00:12: 1/1/0/0/0) |
| API Activity viwiki | `curl "http://localhost:18000/api/v1/activity?wiki=viwiki"` | 1 cửa sổ (00:00: 1/0/1/0/0) |
| Dashboard AppTest (Backend thật) | `$env:PYTHONUTF8=1; $env:DASHBOARD_API_URL="http://localhost:18000"; .venv\Scripts\python -c "..."` | Passed: Overview (5 metrics), System Status (HTTP 200, ready), Trending/Suspicious (HTTP 501) |
| Giao diện trực tiếp | Mở trình duyệt `http://localhost:8501` | Hoạt động đầy đủ 4 trang, auto-refresh 15s |

### Minh chứng hình ảnh (UI Screenshots)
Đã chụp trực tiếp từ Dashboard `http://localhost:8501` và lưu tại `docs/bao-cao-ky-thuat/hinh/W1-Mạnh/`:
1. `Overview (enwiki).png`: Trang Overview chọn `enwiki`, cửa sổ 00:00 UTC (5 thẻ metric và biểu đồ).
2. `Overview (viwiki).png`: Trang Overview chọn `viwiki`, cửa sổ 00:00 UTC (1 sự kiện, 1 trang mới).
3. `System status.png`: Trang System Status (API readiness HTTP 200, Cassandra ready).
4. `Trending.png`: Trang Trending (thông báo HTTP 501 Tuần 2).
