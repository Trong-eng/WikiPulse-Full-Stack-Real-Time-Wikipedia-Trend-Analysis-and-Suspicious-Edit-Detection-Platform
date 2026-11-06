# WikiPulse

Nền tảng học thuật phân tích hoạt động Wikipedia, chuẩn bị mở rộng xu hướng và ưu tiên xem xét chỉnh sửa đáng ngờ. Kế hoạch 4 tuần cho **Trọng, Thành, Linh, Nhân, Mạnh** ở [plans.md](plans.md); tiến độ/evidence ở [docs/checkpoints.md](docs/checkpoints.md).

## Trạng thái triển khai

```text
REPLAY JSONL → Kafka → Spark → Bronze / Silver / Gold Parquet
                               └→ Cassandra → FastAPI → Streamlit Overview
```

CP0 phục vụ activity thật qua Cassandra/API. W2 thêm producer trends/risk/detail ghi Parquet và profile HDFS `full`; API ba nghiệp vụ mới vẫn trả 501 chờ phần Nhân. LIVE collector vẫn chưa triển khai. Phạm vi/evidence: [W2-LINH-01](docs/plans/W2-LINH-01.md), [W2-TRONG-01](docs/plans/W2-TRONG-01.md).

## Yêu cầu

- Docker Desktop/Engine và Docker Compose v2, hỗ trợ ARM64/AMD64; bộ core đã chọn images ARM64.
- Python3.11 hoặc3.12 cho test/script local. Spark chạy Python3.11/Java17 trong container, không cần Java local.
- Gợi ý cấp Docker6–8GB RAM cho core. Build lần đầu cần internet tải images/dependencies; Kafka connector được bake trong Spark image.

## Quick start

```bash
cp .env.example .env
make install
make up
make replay
```

`make up` build/start Kafka, Cassandra, topic/schema init, Spark, API, dashboard theo dependency health. Chờ API healthy rồi `make replay`; fixture timestamp lịch sử nên API/UI dùng cửa sổ có dữ liệu thay vì đồng hồ hiện tại. `make init` dùng khi cần chạy lại topic/schema init (idempotent).

| Service | URL / connection |
|---|---|
| Dashboard | http://localhost:8501 |
| FastAPI | http://localhost:18000 |
| Swagger | http://localhost:18000/docs |
| Health | http://localhost:18000/health |
| Kafka từ host | localhost:19092 |
| Cassandra | Nội bộ Compose: cassandra:9042 |

Cổng8000 host đang có dự án khác, nên API mặc định18000. Đổi API_HOST_PORT/DASHBOARD_HOST_PORT/KAFKA_HOST_PORT trong .env nếu bị chiếm. App gọi broker/database qua Docker network, không dùng localhost bên trong container.

Ví dụ dữ liệu mẫu:

```bash
curl 'http://localhost:18000/api/v1/activity?wiki=enwiki&window=2026-01-01T00%3A00%3A00%2B00%3A00'
```

Window00:00 có enwiki5 edits,1anonymous,1bot; viwiki1new page. Event00:12 dùng tiến watermark để window00:00 finalized ở Gold. Overview cho chọn wiki/window; selected counts không phải global totals. UI refresh15s/manual; Cassandra rows tạm tính; Gold chậm theo watermark10m.

## Kiểm thử

```bash
make test          # unit + API + Streamlit AppTest, không cần cluster
make lint
make config        # validate Compose
make test-spark    # PySpark3.5.6/Java17 trong container
make smoke        # real E2E, stack/volumes test riêng, tự cleanup
make config-full  # validate HDFS overlay/profile
make smoke-full   # E2E HDFS + recreate nodes, phục hồi checkpoints
```

Smoke khởi tạo project riêng, publish fixture hai phase, assert counts cả hai wiki, duplicate/canary exclusion, invalid rows, Bronze/Silver/Gold, analytics Parquet, API/UI/Spark readiness và 501 deferred routes. Nó không seed Cassandra hay xóa data của dev stack. Evidence ở `artifacts/smoke-*/report.json`, `commands.log`, `services.log`.

Để giữ stack test xem lỗi:

```bash
.venv/bin/python scripts/smoke_test.py --keep
# Cleanup đúng project name in report, không dùng project mặc định:
docker compose -p wikipulse-smoke-YYYYMMDDHHMMSS down --volumes
```

`make down` giữ volumes. `make logs` xem logs. `make replay` chạy cùng fixture có ID ổn định; dedup chỉ được cam kết trong watermark horizon, không replay vô hạn vào run cũ. Chạy mới/schema mới cần namespace/output/checkpoint/keyspace mới hoặc dùng smoke cô lập.

## W2 và HDFS

Lần đầu nâng từ W1, dùng `.env.example` mới làm tham chiếu: `PIPELINE_VERSION=0.2.0`, RUN_ID/data/checkpoint và Cassandra namespace mới. Không tái sử dụng Silver v0.1. Compose mặc định `RUN_ID=dev-w2`; `.env` có sẵn vẫn được ưu tiên nên phải cập nhật thủ công.

Compose forward `SPARK_ANALYTICS_SINK` (mặc định `parquet`) và `SPARK_SCORING_PATH` (mặc định `/workspace/config/scoring.yaml`) vào Spark. Scoring file phải tồn tại **trong container**; nếu dùng file tùy chỉnh, mount read-only bằng override. Ý nghĩa analytics ở [processing README](processing/README.md#week-two-analytics). Mode Cassandra W2 cần store của Nhân; hiện thiếu methods và sẽ fail startup rõ ràng.

`make up-full` bật HDFS và chờ health; `make down-full` giữ volumes. Cách chọn project/URI, migrate namespace, readiness và restart: [HDFS README](storage/hdfs/README.md). Core mặc định vẫn local, không tự bật HDFS.

## Cấu trúc và ownership

| Module | Owner tiếp quản |
|---|---|
| shared/config, Compose, Makefile, scripts, docs tích hợp | Trọng |
| ingestion/collector, replay | Thành |
| processing/spark | Linh |
| storage/cassandra, shared/serving, api | Nhân |
| dashboard, acceptance chung | Mạnh |

Đọc [contracts](docs/contracts.md), [architecture](docs/architecture.md), [data flow](docs/data-flow.md), [dictionary](docs/data-dictionary.md), [development](docs/development.md). Mỗi người tiếp quản scaffold/tests rồi thực hiện checkpoint của mình; bảng không tự đánh dấu việc con người đã DONE chỉ vì có baseline.

## Giới hạn hiện tại

MVP một node chưa production-ready. Bronze giữ raw payload có thể chứa username/IP; Silver/API không hiển thị các trường này. Hash có salt là pseudonymization. Không auth/RBAC/HA, không giao dịch nguyên tử qua các sink; Kubernetes/monitor exporters chưa triển khai. Kafka DLQ topic có sẵn; invalid hiện lưu Parquet. LIVE và serving/API trends/risk/detail còn chờ owner. Risk chỉ dùng ưu tiên xem xét, không kết luận vandalism.
