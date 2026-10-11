# Data flow và thời gian

1. Replay giữ nguyên JSON/source ID/event timestamp, thêm ingestion metadata rồi publish Kafka.
2. Bronze append raw payload + topic/partition/offset. Malformed/missing fields sang invalid Parquet.
3. Silver explicit schema, UTC event time, ID ổn định, byte delta và user hash; loại canary/khác wiki allowlist; dedup trong watermark10m.
4. Activity đọc Silver và đếm event-time1m. Update sink ghi absolute counts Cassandra; Append sink ghi Gold đã finalized.
5. API activity đọc wiki partition, mặc định cửa sổ mới nhất có dữ liệu. UI gọi API, không đọc Cassandra trực tiếp.

Các sink không có một giao dịch chung. Retry và checkpoint được test; không cam kết exactly-once xuyên Parquet/Cassandra. Event quá dedup horizon có thể không được phục vụ; Bronze vẫn là nguồn audit. Thay đổi stateful schema cần checkpoint/run mới, không tái dùng checkpoint không tương thích.

Fixture ngày01/01/2026 gồm 5 edit enwiki, 1 new viwiki, duplicate,2 invalid,canary và1 event tại00:12:10 để tiến watermark. Smoke tách hai phase để query downstream nhận dữ liệu gốc trước khi tiến thời gian. Gold kiểm tra window00:00, không chờ window cuối00:12 tự finalized.
