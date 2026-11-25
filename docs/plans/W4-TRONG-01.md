Trạng thái: DONE · Owner: Trọng · Reviewer dự kiến: Cả nhóm · Liên quan: W4-TRONG-01, CP3/CP4

## Mục tiêu

Đóng phạm vi tính năng và chốt ứng viên demo REPLAY/HDFS. Kiểm tra setup từ clone sạch, xử lý lỗi tích hợp trong phạm vi Trọng, làm rõ các điều kiện CP4 còn thiếu.

## Phạm vi / Không làm

Chỉ sửa lỗi kiểm thử/tích hợp và cập nhật tài liệu bàn giao. Các cổng còn phụ thuộc collector LIVE, serving W2, dashboard và evidence trên máy khác được theo dõi theo [checkpoints](../checkpoints.md).

## Các bước

- [x] Tạo nhánh W4 riêng từ `main` sau khi merge W3. Audit mã nguồn và môi trường triển khai.
- [x] Sửa test Compose phụ thuộc `/dev/null` và giới hạn các test mô phỏng Bash vào môi trường có POSIX/Bash. Full smoke kiểm script HDFS trong Linux container.
- [x] Build và chạy unit/lint/config/Spark/full HDFS smoke từ clone sạch, venv mới và namespace test riêng. Ghi đúng SHA và môi trường kiểm tra.
- [x] Chốt trình tự demo REPLAY, evidence và giới hạn. Bàn giao W4 để merge fast-forward.
- [x] Bổ sung bằng chứng máy thứ hai và hoàn tất nghiệm thu CP4 khi CP3, LIVE và các màn hình với dữ liệu thật sẵn sàng.

## Quyết định

- Ứng viên demo đóng phạm vi REPLAY/HDFS với activity và analytics Parquet. Việc nhận xét readiness toàn nhóm dựa trên tiêu chí CP3/CP4.
- Clone kiểm tra trên macOS ARM64 hiện tại, venv mới và build từ source đã checkout. Nghiệm thu máy thứ hai là công việc riêng, cần chạy đúng SHA của ứng viên.

## Nhật ký

- 2026-11-23 — W3 đã merge vào `main` tại `7db6682`, tạo nhánh `trong/w4-trong-01-release-candidate`. Audit thấy phép thử Compose dùng `/dev/null`, bootstrap shell đòi POSIX/Bash. Xác nhận collector LIVE vẫn là stub, ba endpoint serving W2 trả HTTP 501.
- 2026-11-23 — Chạy clone sạch tại `ce71442` và có review độc lập. Tài liệu sau review bổ sung guard kiểm tra tên project trước khi dọn volume. Kiểm tra shell guard với biến thiếu và với tên project cụ thể.

## Kết quả

Ứng viên REPLAY/HDFS kiểm chứng tại `ce7144215899876f102c17e9ca2dda948d65261c`. Clone độc lập `git clone --no-local` trên cùng máy macOS ARM64, checkout SHA, `cp .env.example .env`, cài mới bằng Python 3.12.5. Docker 29.2.1 và Compose 5.1.0. Commit evidence sau đó chỉ cập nhật tài liệu và trạng thái.

| Lệnh trên clone sạch | Kết quả |
|---|---|
| `make test lint config config-full` | 147 passed, lint và hai config exit 0 |
| `make smoke-full` | Build bốn image và smoke REPLAY/HDFS pass. Đọc activity trước khi Spark chạy lại, giữ dải 11 records Kafka và khôi phục đủ 9 checkpoint |
| `make test-spark` | 68 passed, gồm regression của Linh W4 |

Evidence local gồm [report full](../../artifacts/w4-trong/clean-full-report.json), [unit/lint/config](../../artifacts/w4-trong/clone-checks.log), [Spark](../../artifacts/w4-trong/clone-spark.log). Smoke đã dọn project và volume test sau khi kết thúc. Các log là artifact gitignored.

Nghiệm thu W4 còn chờ clone sạch trên máy thứ hai, CP3 toàn nhóm, collector LIVE của Thành, serving W2 của Nhân và xác nhận bốn trang của Mạnh. Các test trên Windows đã được chỉnh để dùng tệp env portable và skip mô phỏng Bash khi thiếu POSIX. Lần này kiểm chứng thực trên macOS ARM64 và Linux containers.

### Kịch bản demo REPLAY/HDFS

Từ clone sạch của SHA ứng viên, dùng Python 3.11 hoặc 3.12 và Docker Compose. Tạo venv/cài dependencies theo [README](../../README.md). Từ root chạy `.venv/bin/python scripts/smoke_test.py --hdfs --keep` (Windows dùng `.venv\Scripts\python.exe`), chờ `status: passed`. Lệnh tạo project riêng và tự chọn cổng trống. `--keep` giữ stack để trình diễn.

1. Mở `dashboard_url` trong `report.json`; chọn Overview và cửa sổ `2026-01-01 00:00 UTC`. Với `enwiki` kỳ vọng 5 sự kiện, 5 chỉnh sửa, 1 ẩn danh, 1 bot. Với `viwiki` kỳ vọng 1 sự kiện, 1 trang mới.
2. Mở System Status và kiểm tra API/Cassandra ready. Đối chiếu activity qua `api_url` và [contract API](../contracts.md#api--nhân--mạnh).
3. Dùng phần `restart_inspection` và `restored_checkpoint_queries` trong report để trình bày Bronze/Silver/Gold, analytics Parquet và khả năng khôi phục. Log chi tiết ở `commands.log` cùng thư mục.

Khi kết thúc, đặt `SMOKE_PROJECT` bằng đúng giá trị `project` trong report của lượt demo rồi chạy:

```sh
docker compose -p "${SMOKE_PROJECT:?Set SMOKE_PROJECT from report.json}" -f docker-compose.yml -f docker-compose.hdfs.yml --profile full down --volumes --remove-orphans
```

Phạm vi bàn giao là hai trang Overview/System Status với dữ liệu REPLAY. Trending/Suspicious còn chờ Cassandra/API W2. Hồ sơ CP4 cần đủ bốn trang, LIVE ≥15 phút và log từ máy thứ hai chạy đúng SHA.
