# Data flow và thời gian

1. Replay giữ nguyên JSON/source ID/event timestamp, thêm ingestion metadata rồi publish Kafka.
2. Bronze append raw payload + topic/partition/offset. Malformed/missing fields sang invalid Parquet.
3. Silver explicit schema, UTC event time, ID ổn định, byte delta và user hash; loại canary/khác wiki allowlist; dedup trong watermark10m.
4. Activity đọc Silver và đếm event-time1m. Update sink ghi absolute counts Cassandra; Append sink ghi Gold đã finalized.
5. API activity đọc wiki partition, mặc định cửa sổ mới nhất có dữ liệu. UI gọi API, không đọc Cassandra trực tiếp.
6. W2 đọc Silver bằng các query riêng: trends 5 phút trượt 1 phút → provisional changelog và Gold finalized; risk → suspicious edits; mọi event → detail. Mặc định ba đầu ra serving này nằm ở Parquet, chưa nối vào API của Nhân. Công thức/khóa/nullable semantics ở [contracts](contracts.md).

Core lưu các tầng và checkpoint trên local volume. Full overlay đưa cả hai sang HDFS với namespace theo RUN_ID; API/Cassandra không đổi. Chuyển schema Silver, scoring hoặc storage phải dùng namespace mới theo [HDFS README](../storage/hdfs/README.md), không ghép dữ liệu v0.1/v0.2 trong run cũ.

Các sink không có một giao dịch chung. Retry và checkpoint được test; không cam kết exactly-once xuyên Parquet/Cassandra. Event quá dedup horizon có thể không được phục vụ; Bronze vẫn là nguồn audit. Thay đổi stateful schema cần checkpoint/run mới, không tái dùng checkpoint không tương thích.

Fixture ngày01/01/2026 gồm 5 edit enwiki, 1 new viwiki, duplicate,2 invalid,canary và1 event tại00:12:10 để tiến watermark. Smoke tách hai phase để activity Gold và hai query trends đều nhận dữ liệu gốc trước khi tiến thời gian. Gold activity kiểm tra window00:00; Gold trends kiểm tra cửa sổ sớm đã chốt, không chờ cửa sổ cuối tự finalized. Smoke full còn recreate HDFS, restart Spark cùng run, đối chiếu query IDs/checkpoints và đọc lại output. Evidence ở [W2-TRONG-01](plans/W2-TRONG-01.md#kết-quả).
