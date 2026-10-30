Trạng thái: DONE · Owner: Linh · Reviewer dự kiến: Trọng, Nhân (không chờ review chung theo yêu cầu người dùng) · Liên quan: W2-LINH-01, BL-THANH-19–21

# W2-LINH-01 — Spark windows, features và scoring

## Mục tiêu

Triển khai producer Spark theo [contract v0.2](../contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02), có golden tests và output tái hiện được để Nhân nối sink/API.

## Phạm vi / Không làm

- Làm: Silver v0.2, canary, scoring YAML được validate, trends 5m/slide1m, risk/detail, query/checkpoint riêng, callback bàn giao và Parquet output khi Cassandra W2 chưa có.
- Không sửa implementation Cassandra/API/collector của owner khác; không triển khai HDFS hay Kafka DLQ trong việc này. Activity CP0 phải giữ regression pass.

## Các bước

- [x] Tests trước cho normalization, scoring, schema, golden results và loader.
- [x] Silver v0.2, trends/risk/detail và các query/output producer.
- [x] Kiểm chứng streaming duplicate/late/restart/finalized, callbacks retry và smoke CP0.
- [x] README/contracts, backlog, evidence; bàn giao bằng commit `feat(spark): implement week-two analytics and scoring` trên nhánh mới.

## Quyết định

- Người dùng ngày 30/10/2026 yêu cầu thực hiện và commit trên nhánh mới, không chờ review chung; không ghi thay xác nhận review của thành viên.
- Revert nhận diện comment bắt đầu bằng Revert/Reverted/Reverting, Undid revision, Undo revision, Rollback/Rolled back (không phân biệt hoa thường); xử lý trước khi loại comment khỏi Silver. Không suy diễn mọi câu chứa từ revert là hoàn tác.
- LARGE_DELETION khi byte_delta <= -large_deletion_bytes; null không kích hoạt; rules chỉ dành edit, bot không nhận ANONYMOUS_EDIT. Default threshold 500 theo config hiện hành.
- Giữ 5 query CP0, bổ sung analytics từ ranh giới Silver. Mặc định output Parquet (provisional trends là changelog tổng tuyệt đối theo batch, không cộng các batch). Mode Cassandra yêu cầu store của Nhân có đủ callbacks và fail rõ nếu chưa có; không âm thầm bỏ dữ liệu.
- Silver thay schema cần RUN_ID/checkpoint/output mới. Config scoring cố định trong một run; không đổi cấu hình rồi tái sử dụng state cũ.

## Nhật ký

- 2026-10-30 — Tạo nhánh `linh/w2-linh-01-analytics` từ `origin/main@ca3d192`; mang theo ghi chú khảo sát W1; bắt đầu test/implementation theo yêu cầu. Chưa commit.
- 2026-10-30 — Red tests bắt được thiếu normalization/analytics; triển khai loader, Silver v0.2, ba DataFrame, bốn query và callback. Suite cuối 66 passed, lightweight 127 passed; smoke Kafka thật pass, inspection analytics pass, stack test đã dọn. Người dùng bỏ yêu cầu chờ review chung; không ghi nhận giả rằng Trọng/Nhân đã review.

## Kết quả

Hoàn tất phần producer của Linh. Base commit `ca3d192bd8be6ddc5f0a52c3634c267834cf3021`; Python host 3.11.5, Docker 29.1.3, Spark image Python 3.11/Java 17/PySpark 3.5.6, PyYAML 6.0.2. Evidence ở `artifacts/linh-w2/`, gói `artifacts/linh-w2-evidence-20261030.zip` (gitignored, đính kèm khi bàn giao).

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Test-first | 2 failed trước implementation (đúng kỳ vọng) | `red-tests.log` |
| Spark/driver/config/streaming | 66 passed, không skip/xfail, 62,11 giây | `spark-final.log` |
| Lightweight toàn repo | 127 passed, 57 deselected, 2 deprecation warnings, 12,03 giây | `unit-tests.log`, `unit-tests.xml` |
| Ruff | All checks passed | `lint.log` |
| CP0 E2E | passed: activity/API/dashboard, Bronze11/invalid2/Silver7/Gold activity2 | `artifacts/smoke-20261030084350-d07a74cacd65480d84457ffa3f1e4255/report.json` |
| Analytics trên cùng Kafka run | events7, suspicious3; risk fixture-002/004/005 = 10/30/20; duplicate không tăng trends | `analytics-inspection.log` |

Gold trends chốt được cửa sổ `2025-12-31T23:56:00Z` (CP0 chỉ tiến tới 00:12:10). Hai page_key 10/11 có edit_count 4/1, unique_editors 3/1, abs_byte_delta 1890/5, score 0.12475/0.022625. Changelog provisional cửa sổ 00:00 có cùng edit counts sau khi lấy batch_id mới nhất theo khóa, không cộng các batch.

Sample LIVE qua Spark: 11 Bronze / 9 Silver / 0 invalid; temporary edit 1/1 được nhận diện anonymous; hai event thiếu/null user có 0 hash non-null. BL-THANH-19/20/21 đã xử lý và có regression assertions.

Lệnh tái hiện từ repo root (venv hiện có ở thư mục cha):

```powershell
..\.venv\Scripts\python.exe -m pip install -r processing/spark/requirements-scoring.txt
docker compose build spark
docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q --capture=tee-sys
$env:PYTHONUTF8='1'
..\.venv\Scripts\python.exe -m pytest -q -m 'not integration and not spark'
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe scripts/smoke_test.py --no-build
```

Lần nghiệm thu dùng `--keep`, copy `artifacts/linh-w2/inspect_cp0_analytics.py` vào Spark container của đúng project smoke, chạy `python /tmp/inspect_cp0_analytics.py --base file:///data/wikipulse/<run_id>` rồi `docker compose -p <project trong report> down --volumes --remove-orphans`. Script inspection nằm trong gói evidence; output chỉ chứa IDs fixture và số liệu tổng hợp. Không cleanup dev stack.

Giới hạn bàn giao: Cassandra W2 vẫn cần Nhân nối store/CQL/endpoints (BL-LINH-02); Compose/env/architecture chung cần Trọng cập nhật (BL-LINH-01). Default Parquet là producer handoff, không tuyên bố endpoints trends/risk đã hoạt động. LIVE collector, HDFS và Kafka DLQ không được triển khai trong commit này. CP1/CP2 và checkpoint của thành viên khác giữ nguyên.
