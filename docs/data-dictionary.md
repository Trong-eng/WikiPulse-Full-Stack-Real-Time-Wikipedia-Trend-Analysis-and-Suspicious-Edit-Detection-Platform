# Data dictionary

| Dataset | Trường chính | Ngữ nghĩa |
|---|---|---|
| Bronze/raw | raw_payload, ingested_at, topic/partition/offset, pipeline_version | Original JSON + provenance, có thể chứa username/IP |
| Bronze/invalid | raw_payload, error_code, detected_at, Kafka metadata | Quarantine; không làm dừng query |
| Silver/events | event_id, event_time, wiki/page, revisions, lengths, byte_delta, user_hash, flags | Event chuẩn hóa/privacy-safe; xem schema đầy đủ docs/contracts.md |
| Gold/activity | wiki, window_start/end, five counts, metric_date/hour | Window finalized bằng watermark10m |
| Cassandra/activity | wiki, window_start/end, five counts, updated_at | Window provisional; key wiki+window_start |

`event_count`: mọi event hợp lệ trong allowlist; `edit_count`: type=edit; `new_page_count`: type=new; `anonymous_edit_count`: edit anon/IP-shaped; `bot_edit_count`: edit có bot=true (cả hai là tập con của edit_count). Serving từ chối row vi phạm `edit_count + new_page_count ≤ event_count`, `anonymous/bot_edit_count ≤ edit_count`, `window_end > window_start`. `byte_delta` null khi thiếu length. Timestamps UTC. Username/IP thô không đi vào Silver hoặc response business.

Trend/risk schemas v0.1 là giao diện chuẩn bị; tính toán và serving ở tuần2. Risk prioritizes review, không kết luận vandalism.
