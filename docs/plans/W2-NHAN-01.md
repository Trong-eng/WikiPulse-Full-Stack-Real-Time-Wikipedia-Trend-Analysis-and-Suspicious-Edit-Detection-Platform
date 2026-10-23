# W2-NHAN-01 — Trends/suspicious/detail: khóa query, capacity, lỗi

Trạng thái: ACTIVE · Owner: Nhân · Reviewer: Linh, Mạnh · Liên quan: [checkpoints](../checkpoints.md), [contracts.md mục Tuần 2](../contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02), BL-THANH-05, BL-THANH-19, BL-THANH-21, BL-THANH-23

## Mục tiêu

Ba endpoint trends, suspicious edits, event detail đọc dữ liệu thật từ Cassandra theo contract v0.2. Sink ghi idempotent và có test trên Cassandra thật. Mọi lỗi API dùng chung một định dạng.

## Phạm vi / Không làm

- Làm: CQL cho 5 bảng mới, store/sink idempotent, 3 endpoint, định dạng lỗi thống nhất (kể cả lỗi validate 422 và 501), test trên fake và Cassandra thật, cập nhật data dictionary và mục tương ứng trong báo cáo.
- Không làm: tính trend/risk và cờ `is_revert` (Linh, W2-LINH-01); trang Trending/Suspicious (Mạnh, W2-MANH-01); TTL và capacity test (W3-NHAN-01).

## Các bước

- [x] Chốt contract v0.2 với Linh và Mạnh trên PR #3
- [ ] Định dạng lỗi thống nhất + handler `RequestValidationError` (không phụ thuộc Linh)
- [ ] Bảng `events_by_id` + endpoint event detail
- [ ] Bảng trends + chỉ mục cửa sổ, sink, endpoint trends, kiểm cap 5.000
- [ ] Bảng suspicious + chỉ mục bucket, sink, endpoint suspicious edits
- [ ] Test trên Cassandra thật cho cả ba đường ghi/đọc
- [ ] Data dictionary, báo cáo kỹ thuật, checkpoint → REVIEW

## Quyết định

- Đã chốt trên PR #3: Spark tính `trend_score`; `REVERT_PATTERN` dựa trên cờ `is_revert` trong Silver; giữ bot edit, không cộng `ANONYMOUS_EDIT` cho bot; temporary account tính là ẩn danh; thiếu user thì `user_hash=null`; event không dính rule có `risk_score=0`, `risk_reasons=[]`; khi trống, trends trả `window_start`/`window_end` null; suspicious edits có trường `disclaimer`.
- Chờ nhóm: ý nghĩa `event_count` so với `edit_count` trên LIVE ([BL-THANH-05](../backlog.md#cần-nhóm-quyết-định)).

## Nhật ký

- 2026-10-15 — soạn bản nháp contract tuần 2 — PR #3
- 2026-10-22 — Linh và Mạnh góp ý trên PR #3; gộp bản chốt vào `docs/contracts.md`, xóa file nháp (BL-THANH-23) — PR #3

## Kết quả

Chưa có.
