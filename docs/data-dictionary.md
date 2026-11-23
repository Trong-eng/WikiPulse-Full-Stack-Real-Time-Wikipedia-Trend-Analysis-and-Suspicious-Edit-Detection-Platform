# Data dictionary

| Dataset | Trường chính | Ngữ nghĩa |
|---|---|---|
| Bronze/raw | raw_payload, ingested_at, topic/partition/offset, pipeline_version | Original JSON + provenance, có thể chứa username/IP |
| Bronze/invalid | raw_payload, error_code, detected_at, Kafka metadata | Quarantine; không làm dừng query |
| Silver/events | event_id, event_time, wiki/page, revisions, lengths, byte_delta, user_hash, flags | Event chuẩn hóa/privacy-safe; xem schema đầy đủ docs/contracts.md |
| Gold/activity | wiki, window_start/end, five counts, metric_date/hour | Window finalized bằng watermark10m |
| Cassandra/activity | wiki, window_start/end, five counts, updated_at | Window provisional; key wiki+window_start |
| Cassandra/page_trends_by_window | wiki, window_start/end, page_key/title, namespace, edit_count, unique_editors, abs_byte_delta, trend_score, updated_at | Cửa sổ 5 phút trượt 1 phút, provisional; key (wiki, window_start) + page_key; top-N đọc cả partition, tối đa 5.000 dòng |
| Cassandra/trend_windows_by_wiki | wiki, window_start, updated_at | Chỉ mục cửa sổ có trend, mới nhất trước; dùng cho "latest" |
| Cassandra/suspicious_edits_by_bucket | wiki, bucket_start, event_id, event_time, page, revision_new, byte_delta, is_anonymous/is_bot, risk_score, risk_reasons | Edit có risk_score > 0; bucket = phút của event_time; không có user_hash |
| Cassandra/suspicious_buckets_by_wiki | wiki, bucket_start, updated_at | Chỉ mục bucket có suspicious edit, mới nhất trước |
| Cassandra/events_by_id | event_id + các cột Silver không định danh, risk_score/reasons, pipeline_version, processed_at | Chi tiết event cho API; TTL 7 ngày; không có user/IP/comment |

`event_count`: mọi event hợp lệ trong allowlist; `edit_count`: type=edit; `new_page_count`: type=new; `anonymous_edit_count`: edit anon/IP-shaped; `bot_edit_count`: edit có bot=true (cả hai là tập con của edit_count). Serving từ chối row vi phạm `edit_count + new_page_count ≤ event_count`, `anonymous/bot_edit_count ≤ edit_count`, `window_end > window_start`. `byte_delta` null khi thiếu length. Timestamps UTC. Username/IP thô không đi vào Silver hoặc response business.

Trend/risk: Spark tính (W2-LINH-01), Cassandra/API phục vụ theo contract v0.2 (W2-NHAN-01). `trend_score` 0–1; `risk_score` 0–100 là tổng trọng số lý do (`LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`; API trả theo thứ tự này). Serving từ chối row có field lạ, trend không đúng 5 phút, `bucket_start` khác phút của `event_time`, suspicious edit có `risk_score` 0. Risk dùng để ưu tiên xem xét, không kết luận vandalism.
