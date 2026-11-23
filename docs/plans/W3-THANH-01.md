Trạng thái: REVIEW · Owner: Thành · Reviewer: Linh · Liên quan: W3-THANH-01, W2-THANH-01, BL-THANH-04

## Mục tiêu

Replay timing gốc, recording cục bộ phục vụ analytics, kiểm chứng Kafka outage và đo Spark backlog; chi tiết bối cảnh ở [lộ trình Thành](thanh-ingestion-4-tuan.md).

## Phạm vi / Không làm

Ingestion/replay, tests và docs của Thành. W2 còn REVIEW/chưa commit: giữ nguyên thay đổi, không commit/push, không sửa module hoặc config của owner khác. Recording giữ title thật theo yêu cầu, chỉ dùng local trong artifacts; không commit dữ liệu LIVE.

## Các bước

- [x] Pha 1: baseline, replay timing gốc và regression; subagent review.
- [x] Pha 2: recording theo ACK, privacy và kiểm thử analytics; subagent review.
- [x] Pha 3: Kafka outage/recovery, đo Spark backlog; subagent review.
- [x] Pha 4: regression, docs, evidence, cleanup và bàn giao; subagent review.

## Quyết định

- Timing gốc ưu tiên meta.dt UTC, fallback epoch; không lùi mốc. Default CLI không đổi.
- Recording giữ title nguồn; title có thể chứa thông tin cá nhân nên chỉ lưu local; Thành xử lý trước khi cân nhắc commit.
- W2 còn chờ Trọng/Linh review và BL-THANH-01–04 còn chờ nhóm; không suy diễn CP3 DONE.

## Nhật ký

- 2026-11-23 — Bắt đầu W3 trên working tree chứa W2 chưa commit; giữ nguyên thay đổi và dùng test-first.
- 2026-11-23 — Pha 1: `pytest replay/tests -q -p no:cacheprovider` → 26 passed. Review phát hiện epoch quá lớn và tốc độ cực nhỏ; regression RED→GREEN, kiểm miền timestamp và delay không hữu hạn.
- 2026-11-23 — Pha 2 review phát hiện path qua symlink/junction, metadata nguồn và test Spark: thêm kiểm tra path (RED→GREEN), ghi rõ recording local có thể chứa danh tính trong title/metadata; Spark thật so sánh risk/trend trên sự kiện tổng hợp pass.
- 2026-11-23 — `pytest ingestion/collector/tests ingestion/tests replay/tests -q -m 'not integration and not spark'` → 73 passed, 2 deselected; test Spark thật trong image `wikipulse-spark:0.1.0` → 1 passed. Recording JSON sai không được ghi, chỉ event hợp lệ đã ACK prefix; chưa khẳng định output hoàn toàn ẩn danh.
- 2026-11-23 — Review pha 3 yêu cầu ràng buộc broker với Docker project/cổng loopback, xác nhận từng ACK và đọc tới end-offset; sửa test và chạy lại trên project/volumes mới. Outage: 4 ID duy nhất, 4 records, 0 bản trùng trong kịch bản test; Kafka stop/start. Catchup: 1.200 ACK, offset đầu 0/0/0, đích 0/1200/0; ba query Kafka của Spark đạt đích sau 8,984 giây, gồm khởi động lại Spark. Không coi đây là Gold finalized hay CP3 DONE. Dọn riêng hai project test.
- 2026-11-23 — Review pha 4 không thấy blocker mới; test file recording tổng hợp → replay → Spark parser/analytics pass, suite Spark 68 passed. Smoke HDFS pass; recording thực giữ title/metadata nguồn chỉ được lưu local. Bàn giao REVIEW, chờ Linh và phụ thuộc W2.

## Kết quả

### Evidence kiểm thử ngày 23/11/2026

- `$env:DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -m 'not integration and not spark' --tb=line` → 180 passed, 5 skipped, 63 deselected; 26 dependency warnings. `ruff check .` và `git diff --check` → exit 0. Workaround Windows: BL-THANH-38.
- Test recording tổng hợp → file → `run_replay` → Spark parser/risk/trend: `docker run --rm --mount "type=bind,src=<repo>,dst=/workspace" -w /workspace wikipulse-spark:0.1.0 python -m pytest ingestion/collector/tests/test_recording_spark.py -q -p no:cacheprovider` → 1 passed. Không chứng minh toàn bộ Kafka→API. Suite `processing/spark/tests` cùng image/lệnh tương ứng → 68 passed.
- Outage thật trên Docker project `wikipulse-thanh-w3-outage`: `$env:WIKIPULSE_OUTAGE_PROJECT='wikipulse-thanh-w3-outage'; $env:WIKIPULSE_TEST_KAFKA='127.0.0.1:39092'; .\.venv\Scripts\python.exe -m pytest ingestion/collector/tests/test_outage_integration.py -q -s -p no:cacheprovider` → 1 passed; `unique=4 records=4 duplicates=0`. Hai future chờ trong outage; sau phục hồi đọc tới end-offset đã chốt. Không chứng minh không mất/trùng trong mọi điều kiện.
- Đo backlog trên project mới `wikipulse-thanh-w3-catchup`, `RUN_ID=w3-catchup`: `$env:WIKIPULSE_CATCHUP_PROJECT='wikipulse-thanh-w3-catchup'; $env:WIKIPULSE_TEST_KAFKA='127.0.0.1:49092'; .\.venv\Scripts\python.exe -m pytest ingestion/collector/tests/test_backlog_integration.py -q -s -p no:cacheprovider` → 1 passed; 1.200 ACK, offsets đầu `{0:0,1:0,2:0}`, đích `{0:0,1:1200,2:0}`; `bronze_raw`, `bronze_invalid`, `silver_events` đạt đích sau 8,984 giây tính từ khi gửi xong, gồm khởi động lại Spark. Không đo Gold hay độ trễ end-to-end. Hai project/volumes test đã dọn đúng tên sau khi chạy.
- `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe scripts\smoke_test.py --hdfs` → exit 0, `status=passed`; Bronze 11, invalid 2, Silver 7, 9 checkpoint phục hồi. Report local gitignored: `artifacts/smoke-20261123093731-1cb4ad7ba18d4087bf0f1c851057ad9b/report.json`. Project và volumes smoke đã được kiểm tra là đã dọn.

Linh chưa review và chưa phối hợp xác nhận kết quả backlog; thời gian này chỉ là một lần đo trên môi trường cô lập. W2 vẫn REVIEW, BL-THANH-01–04 chưa được nhóm chốt; không đánh dấu CP3 DONE. Integration test có thể để lại topic trong project test riêng nếu lỗi ở setup/cleanup trước khi teardown chạy; luôn dọn đúng project sau lượt lỗi.
