# Development và bàn giao

Quy trình chuẩn ở [AGENTS.md](../AGENTS.md): đọc plans.md → docs/checkpoints.md → docs/backlog.md → docs/contracts.md → README module → plan của việc đó. Tạo branch `<owner>/<ID>-<slug>`; một PR cho một việc có đầu ra kiểm thử được. Người sở hữu module viết tests/docs; đổi contract cần hai phía review.

Trọng: shared/config, Compose/Makefile/scripts và integration. Thành: ingestion/replay/topic config. Linh: processing. Nhân: storage/cassandra, shared/serving, api. Mạnh: dashboard và acceptance chung.

`make config-full`, `make up-full`, `make smoke-full`, `make acceptance-hdfs`, `make down-full` dùng HDFS overlay/profile. Cách chạy và phạm vi kiểm tra ở [HDFS README](../storage/hdfs/README.md). Spark health xác nhận supervisor và đủ query active. Freshness của nguồn cần evidence riêng.

`make install` cài .venv local, `make test` là lightweight suite; Spark tests chạy `make test-spark` trong Python3.11/Java17 container. Full E2E chạy `make smoke`, evidence ở artifacts/smoke-*/report.json và logs. Smoke có Compose project/volumes riêng, cleanup chỉ phạm vi test. `--keep` giữ test stack để xem; tự cleanup bằng đúng project name trong report.

Startup build lần đầu tải dependencies/images. `make down` giữ volumes để restart. Tạo RUN_ID và keyspace mới khi đổi schema/nguồn. Shared Cassandra code dùng low-volume driver iteration. TTL và capacity Cassandra do Nhân theo W3-NHAN-01.

`KAFKA_RAW_RETENTION_MS` cấu hình retention lúc tạo topic raw mới, mặc định `86400000` (24 giờ). `make init` chạy lại theo kiểu idempotent và giữ cấu hình topic đã có. Sau thời gian retention, Kafka có thể xóa segment cũ theo chu kỳ broker. Resume Spark từ offset đã hết hạn cần run/checkpoint mới hoặc nguồn replay phù hợp.
