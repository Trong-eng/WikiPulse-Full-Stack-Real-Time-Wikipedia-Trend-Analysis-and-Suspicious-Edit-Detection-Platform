# Contracts v0.1 — bàn giao tuần 1

Các quy ước này là điểm nối cho 5 người. Thay đổi phải được bên phát và bên nhận review. Mọi timestamp là UTC; schema_version/pipeline_version hiện là 0.1.0.

## Kafka — Thành → Linh

Topics: `wikipedia.recentchange.raw`, `wikipedia.recentchange.dlq`, `wikipedia.pipeline.alerts`; một broker, replication factor 1, ba partitions cho raw. JSON payload Wikimedia được giữ nguyên và bổ sung `ingested_at` ISO UTC, `collector_version`. Key: `wiki:page_id`, fallback `wiki:title`. `PIPELINE_MODE=REPLAY` mặc định; collector LIVE chỉ có entrypoint bàn giao ở tuần 1.

Fixture JSONL nằm ở `tests/fixtures/recentchange.jsonl`. File chứa cả JSON lỗi có chủ đích. Replay giữ ID/event timestamp; tốc độ chỉ đổi nhịp gửi. Expected results ở `tests/fixtures/expected_activity.json`. Canary domain `canary` được giữ Bronze và bỏ trước business metrics.

## Silver — Linh → sink

Tên module: `processing.spark.wikipulse`. Chuẩn hóa dùng built-in Spark functions, không Python UDF. Schema tối thiểu: event_id string; event_time/ingested_at/processed_at timestamp; wiki/domain/page_title/event_type/user_hash string; page_id/revision_old/revision_new/length_old/length_new/byte_delta long nullable; namespace int nullable; is_anonymous/is_bot/is_minor boolean; kafka_topic string; kafka_partition int; kafka_offset long; pipeline_version string; event_date date; event_hour int. Không raw user/comment trong API hay Silver của scaffold.

ID ưu tiên meta.id; fallback SHA-256 JSON struct ổn định của wiki, page_id, page_title, revision_new, event_time, event_type, recentchange id. user_hash dùng SHA-256(salt + `|` + user); salt lấy từ config, không ghi log. Đây là pseudonymization, không cam kết anonymization. Bronze giữ raw payload để audit/replay.

Validation errors tối thiểu: INVALID_JSON, MISSING_EVENT_TIME, MISSING_WIKI, MISSING_PAGE. Invalid Parquet chứa raw_payload, error_code, Kafka metadata, detected_at. Tuần 1 quarantine bằng Parquet; DLQ topic được tạo nhưng sink Kafka DLQ dành Thành/Linh tuần 2.

## Activity — Linh → Nhân

Window 1 minute/event time; watermark 10 minutes. Output DataFrame được flatten: wiki string; window_start/window_end timestamp; event_count/edit_count/new_page_count/anonymous_edit_count/bot_edit_count long; updated_at timestamp. Counts absolute, không delta. Callback `write_activity_batch(batch_df, batch_id)` gọi `wikipulse_core.serving.CassandraActivityStore.upsert_activity(rows)`; rows là iterable dictionary theo schema trên. `ActivityRow` (shared/wikipulse_core/serving.py) validate wiki identifier, `window_end > window_start` và count nhất quán; row vi phạm làm batch fail thay vì ghi sai. Session Cassandra mở ở driver; không collect toàn dataset vào RAM; dùng toLocalIterator cho scaffold tải thấp.

CQL: `wiki_activity_by_window`, PRIMARY KEY ((wiki), window_start), clustering DESC. Một partition/wiki đủ cho activity MVP; TTL/retention dài hạn dành tuần 3. Query latest đọc row đầu; query window dùng đúng wiki/window_start. Trends/suspicious/event detail: xem mục Tuần 2; score không trong khóa.

## API — Nhân → Mạnh

- GET /health: readiness Cassandra; HTTP 503 khi dependency không sẵn sàng, có mode và implementation status.
- GET /api/v1/activity?wiki=enwiki&window=<ISO-UTC optional>&limit=20: wiki mặc định enwiki; limit 1–100. `window` là window_start, thiếu thì các cửa sổ mới nhất sẵn có, sắp xếp giảm dần.
- GET /api/v1/trends; GET /api/v1/suspicious-edits; GET /api/v1/events/{event_id}: tuần 1 trả HTTP 501 với `code=NOT_IMPLEMENTED` và role/tuần phụ trách; từ W2-NHAN-01 theo mục Tuần 2.

Envelope activity: `{data: ActivityRow[], generated_at: ISO-UTC, source: "cassandra", pipeline_mode: "REPLAY"|"LIVE", provisional: true}`. ActivityRow có 9 trường như output Spark. Dữ liệu trống HTTP 200 data []; timestamp serialization có UTC timezone. Cassandra lỗi khi query: HTTP 503 `{detail: {code: "DEPENDENCY_UNAVAILABLE", source: "cassandra"}}` (có trong OpenAPI). Query sai (limit, wiki ngoài allowlist, window thiếu timezone): HTTP 422. API không giả kết quả và không seed serving vào đường demo.

## Lưu trữ, health và command

`DATA_BASE_PATH` là URI file hoặc hdfs; default `file:///data/wikipulse`; subfolder theo `RUN_ID`. `SPARK_CHECKPOINT_PATH` default `/data/checkpoints`, cũng theo RUN_ID và query. Bronze/Silver partition event_date/event_hour; Gold metric_date/metric_hour/wiki. API/dashboard health phản ánh Cassandra/API thật; trạng thái Kafka configured không được diễn giải thành Kafka reachable.

`make smoke` chạy trong Compose project riêng có RUN_ID và volumes riêng, kiểm tra API counts, raw/invalid/Silver/Gold Parquet và UI HTTP health; không xóa data/checkpoints của dev stack. Test thời gian lịch sử chọn cửa sổ cụ thể thay vì wall clock. Gold finalized xuất hiện khi event-time tiến watermark; fixture gửi theo phase và đợi downstream nhận phase trước khi tiến quá 10 phút.

## Tuần 2 — trends, suspicious edits, event detail (v0.2)

Thống nhất giữa Linh (producer Spark), Nhân (Cassandra/API) và Mạnh (dashboard) trên PR #3. Ràng buộc giữ từ v0.1 và `plans.md`: upsert tổng tuyệt đối theo khóa ổn định; score không trong khóa; không `ALLOW FILTERING`; top-N đọc đủ partition rồi sort, cap 5.000 dòng, vượt cap báo lỗi, không cắt bớt ranking; `limit` 1–100; không lộ username/IP/comment.

### Quy ước chung — Linh

- `page_key`: `page_id` dạng chuỗi, thiếu thì `title:<page_title>`. Dùng cùng quy tắc cho cả ba đầu ra.
- Silver thêm `is_revert` boolean, không null (mặc định false). Suy ra ở bước chuẩn hóa từ các mẫu comment đã chốt, có fixture kiểm thử; không giả định nguồn luôn có tags; Silver/API/log không chứa comment. Ý nghĩa: edit này có dấu hiệu là một lần hoàn tác. Cờ không chứng minh edit là phá hoại, cũng không có nghĩa edit đã bị người khác hoàn tác.
- Ẩn danh gồm cả temporary account (`is_anonymous=true`), phụ thuộc BL-THANH-19. Event thiếu/null user thì `user_hash=null`, không gộp thành một editor giả (BL-THANH-21).
- Trends và risk cần hai item trên xong trước khi nghiệm thu scoring.

### Trends — Linh → Nhân

Cửa sổ 5 phút trượt 1 phút theo event time, watermark 10 phút, Update qua `foreachBatch` như activity. Chỉ tính event `type=edit`, gồm cả bot. Một dòng cho mỗi `(wiki, window_start, page_key)`:

| Trường | Kiểu | Ghi chú |
|---|---|---|
| wiki, page_key, page_title | string | |
| window_start, window_end | timestamp UTC | window_end = window_start + 5 phút |
| namespace | int nullable | |
| edit_count | long | |
| unique_editors | long | `approx_count_distinct(user_hash)`, bỏ qua null |
| abs_byte_delta | long | tổng `abs(byte_delta)`, bỏ qua null; 0 nếu cả nhóm không có giá trị |
| trend_score | double 0–1 | Spark tính: Σ weight × min(giá trị / cap, 1), weights/caps trong `config/scoring.yaml` |
| updated_at | timestamp UTC | |

Cassandra và Gold dùng cùng công thức. Cassandra là kết quả tạm tính, Gold là kết quả chốt; khi cửa sổ còn mở hai bên không bắt buộc bằng nhau.

```sql
CREATE TABLE page_trends_by_window (
    wiki text, window_start timestamp, page_key text,
    window_end timestamp, page_title text, namespace int,
    edit_count bigint, unique_editors bigint, abs_byte_delta bigint,
    trend_score double, updated_at timestamp,
    PRIMARY KEY ((wiki, window_start), page_key)
);
-- Chỉ mục cửa sổ có dữ liệu, để tìm cửa sổ mới nhất mà không quét bảng.
CREATE TABLE trend_windows_by_wiki (
    wiki text, window_start timestamp, updated_at timestamp,
    PRIMARY KEY ((wiki), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
```

Sink ghi `page_trends_by_window` trước rồi upsert `trend_windows_by_wiki`; retry ghi lại cùng giá trị. Ước tính enwiki LIVE dưới 1.000 trang/5 phút, dưới cap.

### Suspicious edits — Linh → Nhân

Một dòng cho mỗi edit có `risk_score > 0`, gồm cả bot. `bucket_start = date_trunc('minute', event_time)`.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| wiki, event_id, page_key, page_title | string | |
| bucket_start, event_time, updated_at | timestamp UTC | |
| revision_new, byte_delta | long nullable | |
| is_anonymous, is_bot | boolean | giữ nguyên để dashboard lọc |
| risk_score | int 0–100 | Σ weight của các lý do, chặn ở `max_score` |
| risk_reasons | array<string> | tập con của `LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT` |

`ANONYMOUS_EDIT` chỉ cộng khi `is_anonymous=true` và `is_bot=false`. Bot vẫn có thể nhận `LARGE_DELETION`, `REVERT_PATTERN`. `REVERT_PATTERN` dựa trên `is_revert`.

```sql
CREATE TABLE suspicious_edits_by_bucket (
    wiki text, bucket_start timestamp, event_id text,
    event_time timestamp, page_key text, page_title text,
    revision_new bigint, byte_delta bigint, is_anonymous boolean, is_bot boolean,
    risk_score int, risk_reasons set<text>, updated_at timestamp,
    PRIMARY KEY ((wiki, bucket_start), event_id)
);
CREATE TABLE suspicious_buckets_by_wiki (
    wiki text, bucket_start timestamp, updated_at timestamp,
    PRIMARY KEY ((wiki), bucket_start)
) WITH CLUSTERING ORDER BY (bucket_start DESC);
```

### Event detail — Linh → Nhân

Ghi mọi event Silver (append qua `foreachBatch`). Event không kích hoạt rule nào có `risk_score=0`, `risk_reasons=[]`. Không có raw user, IP, comment.

```sql
CREATE TABLE events_by_id (
    event_id text PRIMARY KEY,
    wiki text, event_time timestamp, page_key text, page_title text, namespace int,
    event_type text, revision_old bigint, revision_new bigint,
    length_old bigint, length_new bigint, byte_delta bigint,
    is_anonymous boolean, is_bot boolean, is_minor boolean,
    risk_score int, risk_reasons set<text>, pipeline_version text, processed_at timestamp
);
```

TTL đề xuất 7 ngày, chốt ở W3-NHAN-01 sau khi đo dung lượng.

### API — Nhân → Mạnh

- `GET /api/v1/trends?wiki=enwiki&window=<ISO có múi giờ, tùy chọn>&limit=20`: thiếu `window` thì lấy cửa sổ mới nhất trong `trend_windows_by_wiki`. Đọc cả partition, sort `trend_score` giảm dần, hòa thì `edit_count` giảm dần rồi `page_key` tăng dần. Envelope `{data: TrendRow[], window_start, window_end, generated_at, source: "cassandra", pipeline_mode, provisional: true}`; TrendRow gồm các trường của bảng Trends trừ `updated_at`. Không có dữ liệu: 200, `data: []`, `window_start` và `window_end` đều null. Cửa sổ mới nhất luôn chưa đủ 5 phút dữ liệu và còn tăng.
- `GET /api/v1/suspicious-edits?wiki=enwiki&window=<tùy chọn>&minutes=5&min_score=0&limit=20`: đọc `minutes` bucket gần nhất (mặc định 5, tối đa 15) kể từ `window` hoặc bucket mới nhất; tổng số dòng đọc tính vào cap 5.000. Sort `risk_score` giảm dần rồi `event_time` giảm dần. Envelope `{data: SuspiciousEdit[], generated_at, source, pipeline_mode, provisional: true, disclaimer: "Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."}`; SuspiciousEdit gồm đủ các trường của bảng Suspicious, `risk_reasons` là list string. Không trả `user_hash`. Không có dữ liệu: 200, `data: []`.
- `GET /api/v1/events/{event_id}`: 200 `{data: EventDetail, generated_at, source, pipeline_mode}`; EventDetail là các cột của `events_by_id`. Không có: 404 `EVENT_NOT_FOUND`.

### Định dạng lỗi — Nhân → Mạnh

Mọi lỗi dùng `{"detail": {"code": "...", "message": "...", ...}}`; `code` và `message` luôn có, trường khác tùy mã. API override handler `RequestValidationError` của FastAPI để lỗi validate cũng theo dạng này thay vì list mặc định.

| HTTP | code | Khi nào | Trường thêm |
|---|---|---|---|
| 422 | `INVALID_QUERY` | Tham số sai | `fields`: list `{name, message}` |
| 404 | `EVENT_NOT_FOUND` | Không có event_id | |
| 503 | `DEPENDENCY_UNAVAILABLE` | Cassandra lỗi | `source` (đã có ở v0.1) |
| 503 | `CAPACITY_EXCEEDED` | Partition vượt cap 5.000 dòng | |
| 501 | `NOT_IMPLEMENTED` | Endpoint chưa làm | `feature`, `role`, `owner` |

Response 501 hiện có của v0.1 không bọc trong `detail` và chưa có `message`. W2-NHAN-01 đưa nó về dạng trên; dashboard nên đọc được cả hai dạng cho đến khi PR đó merge.
