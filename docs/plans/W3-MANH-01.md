# W3-MANH-01 — Kiểm thử E2E hai chế độ LIVE/REPLAY, Privacy, Freshness và API Outage

Trạng thái: REVIEW · Owner: Mạnh · Reviewer: Trọng · Liên quan: [checkpoints](../checkpoints.md), [contracts.md](../contracts.md), BL-THANH-24, BL-THANH-37

## Mục tiêu

Kiểm chứng toàn bộ luồng dữ liệu End-to-End từ nguồn (`REPLAY` và `LIVE`) qua Kafka $\rightarrow$ Spark $\rightarrow$ Cassandra $\rightarrow$ FastAPI $\rightarrow$ 4 trang Dashboard Streamlit. Xác minh các yêu cầu phi chức năng: bảo vệ quyền riêng tư (privacy), độ tươi dữ liệu tạm tính (freshness mục tiêu 30–60s), khả năng chịu lỗi khi API/Cassandra gián đoạn (outage), và hoàn thiện kịch bản demo cùng ảnh minh chứng báo cáo kỹ thuật.

## Phạm vi / Không làm

- **Làm:**
  - Kiểm tra đồng bộ đồng hồ hệ thống (NTP) trước khi đo độ trễ (`BL-THANH-24`).
  - Kiểm thử E2E chế độ `REPLAY` (với `SPARK_ANALYTICS_SINK=cassandra`) trên cả 4 trang Dashboard.
  - Kiểm thử E2E chế độ `LIVE` (với Wikimedia EventStreams collector và `SPARK_ANALYTICS_SINK=cassandra`), đo độ trễ freshness từ `event_time` tới UI.
  - Kiểm tra privacy trên API response thực tế và toàn bộ 4 trang Dashboard (không lộ username, IP, `user_hash`, `comment`).
  - Kiểm tra kịch bản outage: tắt/bật container `api` hoặc `cassandra`, xác minh UI báo lỗi rõ ràng và tự khôi phục.
  - Chuẩn hóa ảnh chụp 4 trang dữ liệu thật (không dấu, không khoảng trắng) và chèn vào `docs/bao-cao-ky-thuat/main.tex` (`BL-THANH-37`).
- **Không làm:**
  - Không bổ sung tính năng UI mới (đã xong ở `W2-MANH-01`).
  - Không sửa logic Spark/HDFS hay ingestion collector (thuộc phạm vi của Linh, Thành, Trọng).

## Các bước

- [x] Khởi tạo nhánh `manh/w3-manh-01-e2e-qa` từ `main` và lập plan `docs/plans/W3-MANH-01.md`
- [x] Kiểm tra đồng bộ đồng hồ Windows (`w32tm /query /status`) (`BL-THANH-24`)
- [x] Chạy stack E2E chế độ `REPLAY` (`SPARK_ANALYTICS_SINK=cassandra`), xác minh 4 trang Dashboard và chụp ảnh minh chứng
- [x] Chạy stack E2E chế độ `LIVE`, đo độ tươi dữ liệu (freshness 30–60s)
- [x] Kiểm tra Privacy (không lộ username/IP/`user_hash`/`comment`) và kiểm tra API/Cassandra Outage & recovery
- [x] Chèn ảnh vào `docs/bao-cao-ky-thuat/main.tex` (`BL-THANH-37`), điền Regression Checklist vào Kết quả, cập nhật `checkpoints.md`, `backlog.md` và mở PR

## Quyết định

- Khi kiểm thử E2E 4 trang Dashboard với dữ liệu thật, đặt `SPARK_ANALYTICS_SINK=cassandra` (khác mặc định `parquet` dùng cho `smoke_test.py` của Trọng) để Spark ghi đủ bảng `page_trends_by_window`, `suspicious_edits_by_bucket`, `events_by_id` phục vụ API/UI.

## Nhật ký

- 2026-11-25 — Tạo nhánh `manh/w3-manh-01-e2e-qa` từ `main` (`9e559e5`) và lập plan `docs/plans/W3-MANH-01.md`.
- 2026-11-25 — Xác minh đồng bộ NTP Windows (`time.windows.com`, Leap Indicator 0) và chạy thông luồng E2E `REPLAY` với `SPARK_ANALYTICS_SINK=cassandra`: 4 trang Dashboard đọc dữ liệu thật từ Cassandra thành công.
- 2026-11-25 — Chạy E2E chế độ `LIVE` với Wikimedia EventStreams collector, đo độ trễ freshness (`56.41s` từ event_time tới Cassandra; `8.94s` API freshness), kiểm tra Privacy (pass toàn bộ 4 endpoints), kiểm tra API Outage & Recovery (4 trang báo lỗi an toàn và tự phục hồi), chèn 4 ảnh vào `main.tex` và chuyển trạng thái sang REVIEW.

## Kết quả

| Hạng mục kiểm thử | Cách kiểm chứng / Lệnh | Kết quả |
|---|---|---|
| Đồng bộ đồng hồ Windows (`BL-THANH-24`) | `w32tm /query /status` | `Leap Indicator: 0 (no warning)`, đồng bộ `time.windows.com` |
| E2E `REPLAY` (`SPARK_ANALYTICS_SINK=cassandra`) | `docker compose up -d api spark dashboard` + `replay` (11 events) | Pass: Overview (`5/5/0/1/1`), Trending (`Watermark advance`), Suspicious (3 rows + Event Detail `fixture-004`), System Status (`HTTP 200`, `ready`) |
| E2E `LIVE` (Wikimedia EventStreams) | `docker compose --profile live up -d api spark dashboard collector` | Pass: nhận sự kiện thật (`99` events/phút, Trends `Vladimir Lisin`, Suspicious `10` rows), 4 trang Dashboard render không lỗi |
| Freshness (độ tươi dữ liệu LIVE) | Đối chiếu `event_time` $\rightarrow$ `updated_at` Cassandra $\rightarrow$ API | Event-to-Cassandra: **`56.41s`** (đạt mục tiêu 30–60s); API freshness: **`8.94s`** |
| Privacy Audit | Kiểm tra đệ quy JSON của `/activity`, `/trends`, `/suspicious-edits`, `/events/{id}` | Pass: không chứa `user`, `username`, `user_hash`, `ip`, `comment`, `raw_payload` |
| API Outage & Recovery | `docker compose stop api` $\rightarrow$ AppTest 4 trang $\rightarrow$ `docker compose start api` | Outage: 4 trang báo lỗi rõ ràng, không crash/không bịa số 0; Recovery: tự khôi phục (`['238', '143', '2', '6', '74']`) |

### Minh chứng hình ảnh (`docs/bao-cao-ky-thuat/hinh/W3-manh/`)
Đã chụp 4 trang dữ liệu thật, đặt tên chuẩn không dấu và chèn vào `docs/bao-cao-ky-thuat/main.tex`:
- `w3-overview-enwiki.png`
- `w3-trending.png`
- `w3-suspicious-edits.png`
- `w3-system-status.png`
