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

CQL: `wiki_activity_by_window`, PRIMARY KEY ((wiki), window_start), clustering DESC. Một partition/wiki đủ cho activity MVP; TTL/retention dài hạn dành tuần 3. Query latest đọc row đầu; query window dùng đúng wiki/window_start. Query trends/suspicious tương lai: ((wiki, window_start), page_key hoặc event_id); score không trong khóa.

## API — Nhân → Mạnh

- GET /health: readiness Cassandra; HTTP 503 khi dependency không sẵn sàng, có mode và implementation status.
- GET /api/v1/activity?wiki=enwiki&window=<ISO-UTC optional>&limit=20: wiki mặc định enwiki; limit 1–100. `window` là window_start, thiếu thì các cửa sổ mới nhất sẵn có, sắp xếp giảm dần.
- GET /api/v1/trends; GET /api/v1/suspicious-edits; GET /api/v1/events/{event_id}: tuần 1 trả HTTP 501 với `code=NOT_IMPLEMENTED` và role/tuần phụ trách.

Envelope activity: `{data: ActivityRow[], generated_at: ISO-UTC, source: "cassandra", pipeline_mode: "REPLAY"|"LIVE", provisional: true}`. ActivityRow có 9 trường như output Spark. Dữ liệu trống HTTP 200 data []; timestamp serialization có UTC timezone. Cassandra lỗi khi query: HTTP 503 `{detail: {code: "DEPENDENCY_UNAVAILABLE", source: "cassandra"}}` (có trong OpenAPI). Query sai (limit, wiki ngoài allowlist, window thiếu timezone): HTTP 422. API không giả kết quả và không seed serving vào đường demo.

## Lưu trữ, health và command

`DATA_BASE_PATH` là URI file hoặc hdfs; default `file:///data/wikipulse`; subfolder theo `RUN_ID`. `SPARK_CHECKPOINT_PATH` default `/data/checkpoints`, cũng theo RUN_ID và query. Bronze/Silver partition event_date/event_hour; Gold metric_date/metric_hour/wiki. API/dashboard health phản ánh Cassandra/API thật; trạng thái Kafka configured không được diễn giải thành Kafka reachable.

`make smoke` chạy trong Compose project riêng có RUN_ID và volumes riêng, kiểm tra API counts, raw/invalid/Silver/Gold Parquet và UI HTTP health; không xóa data/checkpoints của dev stack. Test thời gian lịch sử chọn cửa sổ cụ thể thay vì wall clock. Gold finalized xuất hiện khi event-time tiến watermark; fixture gửi theo phase và đợi downstream nhận phase trước khi tiến quá 10 phút.
