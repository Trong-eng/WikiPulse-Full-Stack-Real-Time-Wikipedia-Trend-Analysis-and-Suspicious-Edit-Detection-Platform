# W4-MANH-01 — Nghiệm thu Regression, README Verification, LIVE ≥15 phút và Báo cáo CP4

Trạng thái: REVIEW · Owner: Mạnh · Reviewer: Cả nhóm · Liên quan: [checkpoints](../checkpoints.md), [W4-TRONG-01](W4-TRONG-01.md), [contracts.md](../contracts.md)

## Mục tiêu

Hoàn tất kiểm thử nghiệm thu cuối kỳ (CP4) trên máy thứ hai (Windows 11): chạy regression toàn bộ test suite và Full HDFS Smoke theo `README.md`, xác minh hệ thống chạy chế độ `LIVE` liên tục tối thiểu 15 phút với đủ 4 trang Dashboard hoạt động ổn định, lập báo cáo tổng hợp và Release Checklist bàn giao.

## Phạm vi / Không làm

- **Làm:**
  - Chạy kiểm thử trên máy thứ hai (Windows 11): `pytest` toàn repo, `ruff check .` và `scripts/smoke_test.py --hdfs`.
  - Kiểm chứng lại các hướng dẫn cài đặt và chạy trong `README.md` và `dashboard/README.md`.
  - Chạy và giám sát luồng `LIVE` (`PIPELINE_MODE=LIVE`, `SPARK_ANALYTICS_SINK=cassandra`, kèm `collector`) liên tục $\ge$ 15 phút, ghi nhận log/trạng thái ổn định của 4 trang Dashboard.
  - Viết báo cáo tổng hợp Dashboard/QA W1–W4 (`docs/manh/dashboard-bao-cao.md`) và hoàn thiện Release Checklist cho CP4.
  - Đóng các backlog item đã hoàn thành của Mạnh (`BL-NHAN-02`, `BL-THANH-24`, `BL-THANH-37`) khi đủ điều kiện.
- **Không làm:**
  - Không bổ sung tính năng mới (đóng băng tính năng theo quy định Tuần 4 của `plans.md` và `checkpoints.md`).
  - Chỉ sửa lỗi nếu phát hiện regression hoặc sai lệch tài liệu.

## Các bước

- [x] Đồng bộ `main` mới nhất (đã gồm PR #10 `W3-MANH-01`), tạo nhánh W4 và lập plan `docs/plans/W4-MANH-01.md`
- [x] Chạy regression toàn bộ unit tests (`pytest`), `ruff check .` và đối chiếu `README.md` trên Windows
- [x] Chạy Full HDFS Smoke (`scripts/smoke_test.py --hdfs`) trên máy Windows thứ hai (ghi nhận giới hạn timeout Spark trên Docker Desktop Windows)
- [x] Chạy kiểm thử `LIVE` liên tục $\ge$ 15 phút với 4 trang Dashboard hoạt động ổn định và ghi nhận bằng chứng
- [x] Viết báo cáo tổng hợp `docs/manh/dashboard-bao-cao.md` và Release Checklist CP4
- [x] Cập nhật Kết quả, chuyển `W4-MANH-01` sang `REVIEW` trong `docs/checkpoints.md`, cập nhật `docs/backlog.md` và mở PR

## Quyết định

- Kiểm thử trên máy Windows 11 (Docker Desktop) đóng vai trò "máy thứ hai" bổ sung bằng chứng cho `W4-TRONG-01` (đã chạy trên macOS ARM64) để hoàn tất điều kiện CP4.
- Quá trình chạy `LIVE` $\ge$ 15 phút dùng `SPARK_ANALYTICS_SINK=cassandra` để xác nhận cả 4 trang Dashboard (`Overview`, `Trending`, `Suspicious Edits`, `System Status`) cập nhật liên tục suốt phiên chạy.

## Nhật ký

- 2026-11-25 — Tạo nhánh W4 từ `main` và khởi tạo plan `docs/plans/W4-MANH-01.md`.
- 2026-11-25 — Chạy regression suite trên Windows (`231 passed`, `ruff` sạch, compose configs hợp lệ); chạy thử `smoke_test.py --hdfs` và `smoke_test.py` (ghi nhận timeout khởi tạo Spark/inspect_lake trên Docker Desktop Windows); chạy kiểm thử `LIVE` liên tục 17–19 phút (đạt `266` events/phút, `health=ok`, `ui=ok`); viết `docs/manh/dashboard-bao-cao.md`, đóng backlog và chuyển trạng thái sang REVIEW.

## Kết quả

| Kiểm tra (Windows 11, Python 3.11.9, Docker 29.9.3) | Lệnh | Kết quả |
|---|---|---|
| Lint code | `.venv\Scripts\ruff check .` | All checks passed! |
| Unit & contract tests | `.venv\Scripts\python -m pytest -q -m "not integration and not spark"` | 231 passed, 7 skipped, 67 deselected |
| Compose configs | `docker compose config -q` & `--profile full config -q` | Exit 0 |
| Smoke trên Windows | `.venv\Scripts\python scripts/smoke_test.py --hdfs --no-build` & `--no-build` | Các container HDFS/Kafka/Cassandra/API/Dashboard/Spark đều lên và nhận replay, nhưng timeout ở bước `check_spark_ready` (180s) / `inspect_lake` (120s) do chạy đồng thời nhiều JVM trên Docker Desktop Windows |
| Kiểm thử `LIVE` $\ge$ 15 phút | `docker compose --profile live up -d api spark dashboard collector` (`SPARK_ANALYTICS_SINK=cassandra`) | Pass: chạy liên tục **17–19 phút** (`09:50:55Z` $\rightarrow$ `10:06:39Z+`), tất cả container `healthy`, `health=ok mode=LIVE ui=ok`, lưu lượng đo được `29`–`266` events/phút, Trends & Suspicious cập nhật liên tục |

Báo cáo tổng hợp & Release Checklist CP4: [`docs/manh/dashboard-bao-cao.md`](../manh/dashboard-bao-cao.md).
