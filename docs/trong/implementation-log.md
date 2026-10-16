# Implementation log — Trọng tuần1 / CP0

Ngày11/10/2026. User yêu cầu lưu kế hoạch plans.md và triển khai việc tuần1 của Trọng, phạm vi đã chốt ở plans.md. Repo baseline chỉ README, không có code cần giữ nguyên; làm trong workspace user chỉ định. Không publish/push hoặc sửa các dự án khác.

## Các bước

- [x] Lưu plans.md, contracts, checkpoints và ownership.
- [x] Config/shared contracts, Compose/Dockerfiles/Makefile, fixtures/replay.
- [x] Ghép baseline Spark activity-only, Cassandra sink/API, dashboard thật.
- [x] Module tests: API21; dashboard34; Spark16 trong Docker. Host lightweight trước smoke fixes79passed.
- [x] Fresh review: smoke endpoint isolation/UI evidence/namespace collision, allowlist, download failures, structured logging.
- [x] Fix review scope: namespace UUID + pins, actual UI AppTest against container API, configured wiki list, curl fail-loud, application JSONlogs.
- [x] Chẩn đoán startup đầu: Kafka image UID1000 không sở hữu empty named volume. Thêm volume-init chown trong đúng volume/project WikiPulse, giữ nonroot broker.
- [x] Fresh unit/lint/config verification:84passed; Ruff/config pass.
- [x] Real isolated E2E smoke: source Kafka → Bronze/invalid/Silver/Gold → Cassandra/API → actual Overview, status passed.
- [x] Chốt checkpoint/evidence và bàn giao owner; CP1/team acceptance chưa tự đánh dấu.

## Quyết định trong triển khai

- Giữ repo user chỉ định, không tạo worktree mới cho repo trống; tránh phân tán plans.md khỏi folder được yêu cầu. Có thể branch/worktree khi nhóm bắt đầu parallel PRs.
- API hostport18000 tránh dự án khác đang dùng8000; URL trong Docker vẫn api:8000. Chi phí đổi port: cập nhật env nếu nhóm dùng cổng khác.
- HDFS chỉ cấu hình dự kiến tuần1, profile thực được owner hoàn thiện tuần2; CP0 kiểm chứng volume local. Đây là ranh giới đã chốt trong kế hoạch.
- Không ghi DONE việc của người khác; baseline đã có chỉ là điểm bàn giao. CP1 vẫn cần người khác chạy lại từ clone sạch.

Raw logs/build outputs ở /private/tmp/wikipulse-*.log, smoke evidence artifacts/<run_id>. Report tóm tắt kiểm chứng sẽ được lưu tracked trong docs/trong/verification.md.
