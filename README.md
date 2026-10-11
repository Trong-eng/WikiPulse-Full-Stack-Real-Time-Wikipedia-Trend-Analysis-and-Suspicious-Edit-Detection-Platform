# WikiPulse

Nền tảng học thuật phân tích hoạt động Wikipedia, chuẩn bị mở rộng xu hướng và ưu tiên xem xét chỉnh sửa đáng ngờ. Kế hoạch 4 tuần cho **Trọng, Thành, Linh, Nhân, Mạnh** ở [plans.md](plans.md); tiến độ/evidence ở [docs/checkpoints.md](docs/checkpoints.md).

## Trạng thái tuần 1 / CP0

```text
REPLAY JSONL → Kafka → Spark → Bronze / Silver / Gold Parquet
                               └→ Cassandra → FastAPI → Streamlit Overview
```

Đã xây khung activity1 phút, normalized schema/privacy-safe hash, watermark/dedup, invalid quarantine, serving tạm tính và Gold finalized. LIVE collector, HDFS, trends/risk/detail là đầu việc tuần2–3. Các endpoint chưa hoàn thiện trả501 và UI ghi rõ owner/tuần; không có dữ liệu giả trên đường demo.

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
```

Smoke khởi tạo project riêng, publish fixture hai phase, assert counts cả hai wiki, duplicate/canary exclusion, invalid rows, Bronze/Silver/Gold Parquet, API health, UI HTTPhealth và501 deferred routes. Nó không seed Cassandra hay xóa data của dev stack. Evidence ở `artifacts/smoke-*/report.json`, `commands.log`, `services.log`.

Để giữ stack test xem lỗi:

```bash
.venv/bin/python scripts/smoke_test.py --keep
# Cleanup đúng project name in report, không dùng project mặc định:
docker compose -p wikipulse-smoke-YYYYMMDDHHMMSS down --volumes
```

`make down` giữ volumes. `make logs` xem logs. `make replay` chạy cùng fixture có ID ổn định; dedup chỉ được cam kết trong watermark horizon, không replay vô hạn vào run cũ. Chạy mới/schema mới cần namespace/output/checkpoint/keyspace mới hoặc dùng smoke cô lập.

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

MVP một node/local chưa production-ready. Bronze giữ raw payload có thể chứa username/IP; Silver/API không hiển thị các trường này. Hash có salt là pseudonymization. Không auth/RBAC/HA, không giao dịch nguyên tử qua các sink, chưa HDFS/Kubernetes deployment/monitor exporters. Kafka DLQ topic có sẵn; invalid hiện lưu Parquet. Trends/risk/detail/LIVE chưa triển khai. Risk tương lai dùng ưu tiên xem xét, không kết luận vandalism.
