# Development và bàn giao

Đọc plans.md → docs/checkpoints.md → docs/contracts.md → README.md. Tạo branch `codex/<role>-<task>` hoặc tên nhóm thống nhất; một PR cho một việc có đầu ra kiểm thử được. Người sở hữu module viết tests/docs; đổi contract cần hai phía review.

Trọng: shared/config, Compose/Makefile/scripts và integration. Thành: ingestion/replay/topic config. Linh: processing. Nhân: storage/cassandra, shared/serving, api. Mạnh: dashboard và acceptance chung.

`make install` cài .venv local, `make test` là lightweight suite; Spark tests chạy `make test-spark` trong Python3.11/Java17 container. Full E2E chạy `make smoke`, evidence ở artifacts/smoke-*/report.json và logs. Smoke có Compose project/volumes riêng, cleanup chỉ phạm vi test. `--keep` giữ test stack để xem; tự cleanup bằng đúng project name trong report.

Startup build lần đầu tải dependencies/images; các lần sau dùng cache. `make down` giữ volumes để restart. Không xóa checkpoint để chữa lỗi rồi ghi vào output cũ; tạo RUN_ID và keyspace mới khi đổi schema/nguồn. Shared Cassandra code dùng low-volume driver iteration, chưa là sink hiệu năng cao. Tuần3 xử lý retention/TTL và đo tải trước khi mở allowlist.
