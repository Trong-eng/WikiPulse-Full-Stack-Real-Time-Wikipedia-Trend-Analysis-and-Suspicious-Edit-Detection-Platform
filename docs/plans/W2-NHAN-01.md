# W2-NHAN-01 — Trends/suspicious/detail: khóa query, capacity, lỗi

Trạng thái: REVIEW · Owner: Nhân · Reviewer: Linh, Mạnh · Liên quan: [checkpoints](../checkpoints.md), [contracts.md mục Tuần 2](../contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02), BL-LINH-02, BL-THANH-05, BL-THANH-19, BL-THANH-21, BL-THANH-23

## Mục tiêu

Ba endpoint trends, suspicious edits, event detail đọc dữ liệu thật từ Cassandra theo contract v0.2. Sink ghi idempotent và có test trên Cassandra thật. Mọi lỗi API dùng chung một định dạng.

## Phạm vi / Không làm

- Làm: CQL cho 5 bảng mới, store/sink idempotent, 3 endpoint, định dạng lỗi thống nhất (kể cả lỗi validate 422 và 501), test trên fake và Cassandra thật, cập nhật data dictionary và mục tương ứng trong báo cáo.
- Không làm: tính trend/risk và cờ `is_revert` (Linh, W2-LINH-01); trang Trending/Suspicious (Mạnh, W2-MANH-01); TTL và capacity test (W3-NHAN-01); đổi mặc định `SPARK_ANALYTICS_SINK` (Trọng, BL-NHAN-01).

## Các bước

- [x] Chốt contract v0.2 với Linh và Mạnh trên PR #3
- [x] Định dạng lỗi thống nhất + handler `RequestValidationError` (không phụ thuộc Linh)
- [x] Bảng `events_by_id` + endpoint event detail
- [x] Bảng trends + chỉ mục cửa sổ, sink, endpoint trends, kiểm cap 5.000
- [x] Bảng suspicious + chỉ mục bucket, sink, endpoint suspicious edits
- [x] Test trên Cassandra thật cho cả ba đường ghi/đọc
- [x] E2E replay → Spark (`SPARK_ANALYTICS_SINK=cassandra`) → Cassandra → API
- [x] Data dictionary, báo cáo kỹ thuật, checkpoint → REVIEW

## Quyết định

- Đã chốt trên PR #3: Spark tính `trend_score`; `REVERT_PATTERN` dựa trên cờ `is_revert` trong Silver; giữ bot edit, không cộng `ANONYMOUS_EDIT` cho bot; temporary account tính là ẩn danh; thiếu user thì `user_hash=null`; event không dính rule có `risk_score=0`, `risk_reasons=[]`; khi trống, trends trả `window_start`/`window_end` null; suspicious edits có trường `disclaimer`.
- Store mới gắn vào `CassandraActivityStore` (Spark đang dùng class này làm store), không tạo class riêng; Linh không phải sửa code.
- Validate từng dòng ở sink như activity: field lạ (ví dụ `user_hash`, `comment`), trend không đúng 5 phút, `bucket_start` khác phút của `event_time`, suspicious `risk_score=0`, lý do ngoài 3 mã → batch fail. Chỉ kiểm các trường Spark luôn có, để không làm stream fail lặp lại vì trường nullable (`page_title`, `namespace`, revision/length).
- Cassandra trả set rỗng là `null`; store đổi về `[]` và trả lý do theo thứ tự `LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`.
- Hòa điểm suspicious: thêm `event_id` tăng dần để thứ tự ổn định; `window` làm tròn xuống phút, đọc bucket trong `(window − minutes, window]` (đã ghi vào contract).
- Giữ mặc định `SPARK_ANALYTICS_SINK=parquet` để không đụng Compose/smoke của Trọng; đề xuất đổi ở BL-NHAN-01.
- Chờ nhóm: ý nghĩa `event_count` so với `edit_count` trên LIVE ([BL-THANH-05](../backlog.md#cần-nhóm-quyết-định)).

## Nhật ký

- 2026-10-15 — soạn bản nháp contract tuần 2 — PR #3
- 2026-10-22 — Linh và Mạnh góp ý trên PR #3; gộp bản chốt vào `docs/contracts.md`, xóa file nháp (BL-THANH-23) — PR #3
- 2026-11-23 — CQL 5 bảng, store ghi/đọc, 3 endpoint, lỗi thống nhất, test fake + Cassandra thật, E2E cassandra mode; sửa tối thiểu smoke (501 → kiểm envelope v0.2); báo cáo: lược đồ, API, đặc tả use case, kết quả — PR #6

## Kết quả

Môi trường: Windows 11, Python 3.12.10, Docker 29.9.2, Cassandra 4.1.8.

- Test nhẹ: `.venv/Scripts/python -m pytest -q -m "not integration and not spark"` → 179 passed, 5 skipped; riêng `api/tests` 68 passed (bỏ 2 test `tests/test_deployment.py` lỗi `unknown flag: --env-file` do Docker CLI trên máy này; fail y hệt trên `main` 0c59b03). `ruff check .` sạch.
- Cassandra thật: `docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8` rồi `CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 python -m pytest -m integration api/tests` → 8 passed (retry trends giữ 1 dòng/trang, cửa sổ mới nhất qua chỉ mục, range bucket không `ALLOW FILTERING`, set rỗng → `[]`, TTL, cap 5.000).
- E2E: compose project riêng, `SPARK_ANALYTICS_SINK=cassandra`, replay 11 bản ghi fixture. 9 query Spark active (có `trends_cassandra`, `suspicious_cassandra`, `events_cassandra`). API trả:
  - `/api/v1/suspicious-edits?minutes=15`: `fixture-004` 30 `LARGE_DELETION`, `fixture-005` 20 `REVERT_PATTERN`, `fixture-002` 10 `ANONYMOUS_EDIT`, có `disclaimer`;
  - `/api/v1/trends?window=2026-01-01T00:00:00Z` và `2025-12-31T23:56:00Z`: trang 10 (4 edit, 3 editor, 1890 byte, 0.12475), trang 11 (1, 1, 5, 0.022625);
  - `events_by_id` 7 dòng; `/events/fixture-001` có `risk_score 0`, `risk_reasons []`; `/events/nope` → 404.

  Trùng với kỳ vọng độc lập của Linh trong `scripts/inspect_lake.py` (Parquet mode).
