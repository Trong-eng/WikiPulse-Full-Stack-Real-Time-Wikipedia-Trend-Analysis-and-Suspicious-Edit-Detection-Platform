# WikiPulse — Khung end-to-end và kế hoạch 4 tuần cho 5 người

**Kế hoạch đã thống nhất:** Trọng phụ trách core/khung/hạ tầng/tích hợp; Thành phụ trách ingestion/Kafka/replay; Linh phụ trách Spark/analytics; Nhân phụ trách Cassandra/sink/API; Mạnh phụ trách dashboard/QA. Ngày lưu: 11/10/2026. Tuần tính từ ngày kickoff của nhóm, không tự suy diễn rằng tuần đã hoàn thành theo lịch.

## 1. Mục tiêu và phạm vi

Dựa trên tài liệu `WikiPulse_Coding_Agent_Plan.md`, chia công việc thành hai phần:

- **Trước mắt:** dựng khung chạy được luồng REPLAY end-to-end, chuẩn hóa giao diện module và tạo checkpoint cho nhóm.
- **Sau 4 tuần:** MVP chạy LIVE/REPLAY, lưu Bronze/Silver/Gold trên HDFS, phục vụ qua Cassandra → FastAPI → Streamlit.

Khoảng **10–15 giờ/người/tuần**, lấy 12 giờ làm mức phân bổ: 8 giờ phát triển, 2 giờ review/tích hợp, 2 giờ dự phòng. Công việc dựng khung của Trọng nằm trong tuần 1.

Kubernetes và monitoring ở mức skeleton. ML, HA, cloud deployment, backfill và benchmark chuyên sâu thuộc backlog. Tài liệu đính kèm là nguồn yêu cầu tham khảo; phạm vi và phân công đã chốt trong cuộc trao đổi này là phạm vi triển khai.

## 2. Khung cần xây ngay — CP0

```text
Fixture REPLAY → Kafka → Spark → Bronze/Silver/Gold Parquet
                                  └→ Cassandra → FastAPI → Overview
```

CP0 chỉ cần nghiệp vụ **đếm hoạt động theo wiki trong cửa sổ 1 phút**. Nghiệp vụ còn lại có contract, vị trí mở rộng và trạng thái chưa triển khai.

### Bộ khung bàn giao

- Monorepo có ingestion, processing, replay, storage, API, dashboard, deployment, monitoring, tests và docs.
- Compose mặc định: một Kafka broker, Spark local, một Cassandra node, API, dashboard; Parquet dùng volume local.
- Profile `full` cho HDFS hoàn thiện trong tuần 2–3; tuần 1 có cấu hình dự kiến và hướng dẫn bàn giao.
- `.env.example`, Dockerfiles, khởi tạo topics/Cassandra, cấu hình ngoài mã nguồn, structured logs.
- `make up`, `make init`, `make replay`, `make smoke`, `make test`, `make logs`, `make down`.
- Fixture cố định, expected results độc lập, smoke test chứng minh toàn bộ luồng.
- Bốn trang dashboard; Overview đọc dữ liệu thật. Trang chưa hoàn thiện ghi rõ trạng thái.
- Kiến trúc, contracts, phân công và bảng checkpoint. DONE cần bằng chứng kiểm thử.

### Giao diện chung

| Giao diện | Quy ước |
|---|---|
| Kafka | Payload nguồn kèm `ingested_at`, `collector_version`; key theo wiki/page |
| Silver | `event_id`, event time UTC, wiki/page, revision, byte delta, `user_hash`, metadata Kafka; không username/IP thô |
| Spark → Cassandra | DataFrame schema cố định; Linh sở hữu đầu ra, Nhân sở hữu sink |
| API | `/health`, `/api/v1/activity`, `/api/v1/trends`, `/api/v1/suspicious-edits`, `/api/v1/events/{event_id}` |
| Response | Data, mode LIVE/REPLAY, cửa sổ, thời điểm cập nhật và trạng thái tạm tính |

CP0 hoàn thiện `/health` và `/activity`; route khác có typed schema và phản hồi chưa triển khai rõ ràng.

### Quyết định kỹ thuật

- Một entrypoint Spark quản lý nhiều query/checkpoint riêng: Kafka → Bronze/invalid; dedup → Silver; Silver → Cassandra tạm tính; Silver → Gold cửa sổ đã chốt. Không ghép dedup và aggregation vào một query Update mode.
- Watermark 10 phút. Activity: 1 phút. Trends: 5 phút, trượt 1 phút. Trigger mục tiêu 10 giây; UI refresh 15 giây. Độ trễ tạm tính mục tiêu 30–60 giây ở tải demo, được đo thực tế.
- Cassandra dùng khóa ổn định và upsert tổng tuyệt đối; không đưa score thay đổi vào khóa, không cộng lại khi retry. Không tuyên bố exactly-once xuyên tất cả sink.
- Top-N đọc đầy đủ partition wiki/cửa sổ rồi sort. Cap demo 5.000 dòng; vượt cap trả lỗi rõ, không cắt cụt ranking. Không `ALLOW FILTERING`.
- API chọn cửa sổ mới nhất có dữ liệu. Demo mặc định `enwiki,viwiki`; mở rộng bằng cấu hình. `limit` tối đa 100.
- Risk MVP: `LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`; burst/rapid edits thuộc backlog. Trend chuẩn hóa bằng caps cấu hình; không dùng min/max của microbatch.
- Event ID ưu tiên ID nguồn, fallback hash trường ổn định; không dùng thời gian ingest/process.
- Replay giữ event time/ID, tốc độ chỉ đổi nhịp gửi; mỗi smoke run dùng namespace dữ liệu/checkpoint riêng. Fixture có event hợp lệ tiến thời gian đủ xa để đóng cửa sổ kiểm thử.
- API/dashboard không lộ username/IP; risk chỉ ưu tiên xem xét, không kết luận phá hoại.

## 3. Phân công theo 4 tuần

| Người / vai trò | Tuần 1 — Khung và replay | Tuần 2 — Nghiệp vụ và LIVE | Tuần 3 — HDFS và tích hợp | Tuần 4 — Kiểm thử/bàn giao |
|---|---|---|---|---|
| **Trọng — Core/hạ tầng/tích hợp** | Monorepo, Compose, config, contracts, Makefile; ghép/nghiệm thu CP0 | Profile HDFS, health/readiness; tích hợp hai lần/tuần | Full stack HDFS; Kubernetes/monitoring skeleton; persistence | Đóng băng tính năng, lỗi tích hợp, clone sạch, chốt demo |
| **Thành — Ingestion/Kafka/replay** | Topics, producer, fixtures, replay, message key | SSE collector, reconnect/backoff/counters; payload thống nhất | Replay speed; mất kết nối/Kafka lỗi; duplicate/invalid/canary | Sửa lỗi, runbook ingestion, demo nguồn dữ liệu |
| **Linh — Spark/analytics** | Schema, validation, event ID, Silver, activity tối thiểu | Dedup/watermark, windows, features/scoring, serving tạm tính | Bronze/Silver/Gold HDFS; late data/finalized/checkpoint | Golden results, correctness, công thức và giới hạn |
| **Nhân — Cassandra/sink/API** | CQL/init, sink tối thiểu, activity API, contracts | Sink/endpoints, validation/error handling, partition queries | Upsert/retry/latest window/detail/capacity | Regression, OpenAPI/data dictionary/runbook |
| **Mạnh — Dashboard/QA** | Bốn trang/API client/Overview thật; checklist | Trending/Suspicious/System Status; filters/error/empty | Smoke hai mode; privacy/freshness/API outage | Regression, README verification, demo/video/evidence |

Mỗi owner viết unit tests và tài liệu module. Mạnh phụ trách acceptance chung. Trọng review/tích hợp, không nhận toàn bộ lỗi của các module. Fixtures/contracts cho phép phát triển song song trước khi LIVE hoàn thiện.

## 4. Checkpoint và tiến độ

| Mốc | Điều kiện DONE |
|---|---|
| **CP0 — Khung, trong tuần 1** | Replay → Kafka → Spark → Parquet/Cassandra → API → Overview; dữ liệu thật, smoke và hướng dẫn tái hiện |
| **CP1 — Cuối tuần 1** | CP0 được người khác chạy lại; 5 người có module, contracts, đầu việc và test đầu tiên |
| **CP2 — Cuối tuần 2** | LIVE/REPLAY, windows/scoring đúng fixtures; UI thật/tạm tính; HDFS profile khởi động |
| **CP3 — Cuối tuần 3** | E2E HDFS thật; Bronze/Silver/Gold, dedup, late data, restart và retry được kiểm chứng |
| **CP4 — Cuối tuần 4** | Clone sạch trên máy thứ hai; replay smoke pass; LIVE ≥15 phút; bốn trang hoạt động; đủ docs/evidence |

Bảng thực thi: [`docs/checkpoints.md`](docs/checkpoints.md).

Mỗi việc có `ID · Tuần · Owner · Reviewer · Phụ thuộc · Đầu ra · Tiêu chí nghiệm thu · Ước lượng · Trạng thái · Bằng chứng`. Mã ví dụ `W2-THANH-01`. Trạng thái `TODO → IN_PROGRESS → REVIEW → DONE`, hoặc `BLOCKED`.

Cập nhật khi đổi trạng thái; tích hợp giữa tuần/nghiệm thu cuối tuần. Đổi contract cần hai phía review. Tuần 4 chỉ sửa lỗi và bàn giao.

## 5. Kiểm thử và hoàn thành

- Parsing/validation: JSON lỗi, thiếu trường, canary; invalid được lưu riêng và không làm dừng query.
- Event ID ổn định; duplicate qua hai microbatch không tăng đếm trong dedup horizon.
- Windows, byte delta, risk reasons, trend đúng expected results độc lập; late data sửa cửa sổ còn mở.
- Replay giữ thời gian/ID, có dữ liệu tiến watermark; kiểm tra cửa sổ chỉ định, không chờ cửa sổ cuối tự chốt.
- Restart Spark với checkpoint cũ; Cassandra retry không cộng đôi hoặc thêm hàng logic.
- API/UI: empty, dependency outage, capacity, historical replay, nhãn tạm tính.
- HDFS: đọc lại ba tầng Parquet, dữ liệu bền qua restart.
- Đo độ trễ demo: provisional mục tiêu 30–60 giây; Gold chờ watermark không có mục tiêu này.

Máy phát triển Apple M3, 16 GB RAM; ưu tiên ARM64, một node; HDFS NameNode/DataNode đơn, replication 1. Không tự động bật HDFS khi chưa được kiểm chứng.

**Lần triển khai trước mắt kết thúc ở CP0 và bộ checkpoint đã phân công.** Nghiệp vụ còn lại hoàn thiện theo 4 tuần trên.
