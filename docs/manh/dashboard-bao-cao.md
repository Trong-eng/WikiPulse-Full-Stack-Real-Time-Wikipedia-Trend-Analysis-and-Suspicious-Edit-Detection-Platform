# Tổng hợp công việc Dashboard & QA — Mạnh (Tuần 1–4)

Tài liệu tổng hợp toàn bộ kết quả triển khai module `dashboard/` và kiểm thử chấp nhận (QA / E2E) của Mạnh từ Tuần 1 đến Tuần 4. Chi tiết lệnh chạy và minh chứng từng tuần nằm tại các plan tương ứng (`docs/plans/W1-MANH-01.md` đến `W4-MANH-01.md`).

## 1. Tóm tắt tiến độ 4 tuần

| Tuần | Plan | Nội dung chính | Trạng thái |
|---|---|---|---|
| Tuần 1 | [`W1-MANH-01`](../plans/W1-MANH-01.md) | Tiếp quản 4 trang Streamlit + `APIClient`, chạy lại CP0 trên Windows, viết `dashboard/README.md` | REVIEW (PR #4) |
| Tuần 2 | [`W2-MANH-01`](../plans/W2-MANH-01.md) | Kết nối API thật cho Trending, Suspicious Edits, Event Detail theo contract v0.2; sửa lỗi UTC trên biểu đồ Overview; cập nhật `dashboard/tests/` | REVIEW (PR #9) |
| Tuần 3 | [`W3-MANH-01`](../plans/W3-MANH-01.md) | Đồng bộ NTP Windows (`BL-THANH-24`); E2E `REPLAY` và `LIVE`; đo freshness (`56.41s`); Privacy Audit; API Outage & Recovery; chèn ảnh báo cáo (`BL-THANH-37`) | REVIEW (PR #10) |
| Tuần 4 | [`W4-MANH-01`](../plans/W4-MANH-01.md) | Regression trên máy thứ hai (Windows 11); kiểm thử `LIVE` liên tục $\ge$ 15 phút (đạt 17–19 phút ổn định); hoàn thiện Release Checklist CP4 | REVIEW |

## 2. Kiến trúc và chất lượng module Dashboard

- **4 trang giao diện (`dashboard/views/`):**
  - `overview.py`: Thống kê cửa sổ 1 phút (`event_count`, `edit_count`, `new_page_count`, `anonymous_edit_count`, `bot_edit_count`) và biểu đồ cột theo trục chuỗi `YYYY-MM-DD HH:MM UTC` (không bị lệch sang múi giờ trình duyệt).
  - `trending.py`: Bảng xếp hạng Top-N theo `trend_score` (cửa sổ 5 phút trượt 1 phút), bộ lọc `limit`, liên kết trực tiếp tới bài viết Wikipedia và trạng thái rỗng (`data: []`, `window_start: null`).
  - `suspicious_edits.py`: Danh sách chỉnh sửa ưu tiên xem xét với bộ lọc `minutes` (1–15), `min_score` (0–100), `limit`, checkbox ẩn/hiện bot edits, nút xem chi tiết sự kiện (`/api/v1/events/{event_id}`) và câu khuyến cáo bắt buộc.
  - `system_status.py`: Kiểm tra readiness thực tế của API và Cassandra qua `/health`.
- **An toàn dữ liệu & Privacy (`dashboard/api_client.py`):**
  - Validate toàn bộ payload từ API trước khi render; từ chối hiển thị nếu phát hiện các trường nhạy cảm (`user_hash`, `comment`, `username`, `ip`).
  - Bắt rõ các mã lỗi theo chuẩn `{"detail": {"code", "message", ...}}` gồm `CAPACITY_EXCEEDED` (503), `DEPENDENCY_UNAVAILABLE` (503), `EVENT_NOT_FOUND` (404), `INVALID_QUERY` (422).

## 3. Release Checklist CP4 (Máy thứ hai — Windows 11)

- [x] `ruff check .` sạch lỗi (`All checks passed!`).
- [x] Unit & contract tests: `231 passed, 7 skipped, 67 deselected` (trong đó `dashboard/tests`: `43 passed`).
- [x] `docker compose config -q` và `docker compose -f docker-compose.yml -f docker-compose.hdfs.yml --profile full config -q` hợp lệ.
- [x] E2E chế độ `REPLAY` (`SPARK_ANALYTICS_SINK=cassandra`): cả 4 trang hiển thị đúng dữ liệu từ fixture.
- [x] E2E chế độ `LIVE` liên tục **$\ge$ 15 phút** (đo thực tế 17–19 phút, tối đa `266` events/phút trên `enwiki`, 0 lỗi, 4 trang hoạt động ổn định).
- [x] Privacy Audit: 0 rò rỉ `username`, `IP`, `user_hash`, `comment`.
- [x] Outage & Recovery: tắt/bật container `api`, 4 trang báo lỗi rõ ràng và tự phục hồi.
- [x] Tài liệu & ảnh minh chứng: `dashboard/README.md`, `docs/bao-cao-ky-thuat/chapters/04-phan-tich-thiet-ke.tex`, `05-kiem-thu-danh-gia.tex` và 4 ảnh tại `docs/bao-cao-ky-thuat/hinh/W3-manh/`.
