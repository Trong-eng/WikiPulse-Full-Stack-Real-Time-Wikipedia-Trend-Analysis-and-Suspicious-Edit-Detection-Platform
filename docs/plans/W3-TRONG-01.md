Trạng thái: DONE · Owner: Trọng · Reviewer dự kiến: Linh, đã có review kỹ thuật độc lập · Liên quan: W3-TRONG-01, BL-THANH-08, CP2/CP3

## Mục tiêu

Nghiệm thu persistence của full stack HDFS, chạy acceptance late/retry/restart của Linh trên cấu hình dùng chung và bàn giao Kubernetes/monitoring skeleton.

## Phạm vi / Không làm

Compose, Makefile, HDFS, scripts tích hợp, triển khai và docs của Trọng. Dùng runner và fixture của Linh; CP2/CP3 toàn nhóm phụ thuộc LIVE và serving W2 của các owner tương ứng.

## Các bước

- [x] Kiểm tra ancestor, fast-forward cả Linh W3/W4 vào main; tạo nhánh W3 từ `d818855`.
- [x] Kiểm chứng full smoke phục hồi Kafka/HDFS/Cassandra và Spark checkpoint; chạy runner acceptance của Linh qua target `acceptance-hdfs` (biến thể `--no-build` sau build).
- [x] Kiểm chứng retention topic raw mới (BL-THANH-08) và giữ cấu hình topic đang có.
- [x] Thêm Kubernetes skeleton stateless có probes và cấu hình phụ thuộc ngoài cluster; monitoring skeleton có kiểm tra readiness thực.
- [x] Chạy kiểm tra, cập nhật docs/backlog và review. Bàn giao commit W3 để merge fast-forward.

## Quyết định

- Kubernetes chỉ chạy API/dashboard với image đã build và dependencies bên ngoài. Collector để `replicas: 0` đến khi có implementation. HDFS, Kafka, Spark và Cassandra tiếp tục nghiệm thu bằng Compose.
- Retention raw mặc định một ngày cho topic mới; cấu hình topic cũ cần thay đổi vận hành riêng để tránh xóa dữ liệu đang có.
- Monitoring tự chọn bằng profile riêng; dùng readiness HTTP thay vì giả định ứng dụng đã có endpoint metrics.

## Nhật ký

- 2026-11-23 — `git merge --ff-only origin/linh/w4-linh-01-correctness` exit 0; main `312c086` → `d818855`, gồm `a38d51d`. Tạo nhánh `trong/w3-trong-01-hdfs-integration`.
- 2026-11-23 — Test trước bắt được hai thiếu sót về kiểm tra persistence qua boundary. Review độc lập đề nghị kiểm tra cả earliest/latest Kafka và cách ly retention của runner. Đã cập nhật và chạy lại unit, lint, Compose config.
- 2026-11-23 — Full smoke và acceptance 7 phase pass trên Docker ARM64. Bàn giao bằng commit `feat(infra): verify full-stack persistence and add deployment skeletons`.

## Kết quả

`kubectl kustomize deploy/kubernetes` render 7 tài nguyên; kiểm tra namespace, selectors, probe endpoints và collector `replicas: 0`. Job khởi tạo Cassandra là bước riêng đã parse YAML. Kiểm chứng manifests thực hiện offline.

Compose monitoring config, `promtool check config`, `blackbox --config.check` đều exit 0 trên ARM64. Runtime fixture HTTP cô lập xác nhận API `200` → `probe_success=1`, dashboard `503` → `0`, rồi dashboard hồi phục `200` → `1`. Lệnh chạy và query ở [monitoring README](../../monitoring/README.md).

`.venv/bin/python scripts/smoke_test.py --hdfs --no-build` sau `docker compose build spark api replay dashboard` trả exit 0. [Report smoke](../../artifacts/smoke-20261123022707-0800a07a765a43ceac24975224657db9/report.json) xác nhận 11 Kafka records còn trong range offset, Cassandra activity đọc được qua API trước khi Spark resume, 9 query checkpoint giữ nguyên ID, 3 lớp Parquet và analytics đọc đúng trước/sau recreate. `kafka-configs --describe` trả về `retention.ms=86400000` sau khi init lại với giá trị 48 giờ. Runner tự dọn project test.

`KAFKA_RAW_RETENTION_MS=86400000 .venv/bin/python -m processing.spark.acceptance.run_hdfs --no-build` exit 0. [Report acceptance](../../artifacts/w3-20261123023044-97376d056893/report.json) gồm 7 phase pass, xác nhận khôi phục 9 checkpoint, retry không tăng số row activity, late data và Gold finalized đúng fixture. Runner tự dọn project test. Các report nằm trong `artifacts/` local, có thể tái tạo bằng `make smoke-full` và `make acceptance-hdfs`.

`make test`: 147 passed, 59 deselected. `make lint`, `make config`, `make config-full`, `bash -n scripts/create_topics.sh`, `git diff --check`: exit 0. Bằng chứng trên phạm vi REPLAY và producer Spark. LIVE và serving/API đầy đủ vẫn là điều kiện nghiệm thu chung CP2/CP3.
