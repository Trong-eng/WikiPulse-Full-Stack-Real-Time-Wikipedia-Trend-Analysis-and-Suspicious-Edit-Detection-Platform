Trạng thái: DONE · Owner: Thành · Reviewer: Trọng (người yêu cầu đại diện xác nhận) · Liên quan: W4-THANH-01, CP4

## Mục tiêu

Tự động chuẩn bị EC2 qua Terraform và cung cấp một lệnh verify REPLAY, kèm hướng dẫn tái hiện.

## Phạm vi / Không làm

Terraform và script thuộc ingestion/collector, README module, kiểm thử mô phỏng và EC2 tạm; không đổi contract, không commit/push.

## Các bước

- [x] Viết test lỗi trước, triển khai bootstrap/verify và cấu hình SHA qua Terraform.
- [x] Viết README Terraform và di chuyển runbook từ README collector.
- [x] Kiểm thử local và EC2 thật trong giới hạn chi phí dự kiến 5 USD; lưu evidence, dọn tài nguyên.

## Quyết định

- SHA 40 ký tự bắt buộc; verify chỉ REPLAY core, giữ timer 3 giờ và SSM.

## Nhật ký

- 2026-11-26 — Bắt đầu theo yêu cầu; bảo toàn thay đổi sẵn có trong workspace.
- 2026-11-26 — Test verifier RED vì script chưa tồn tại; triển khai Terraform, user data, bootstrap, verify và truyền SHA vào watchdog. Test POSIX trong container đạt 8; Terraform fmt/validate và Ruff đạt. SHA `bad` bị Terraform plan từ chối.
- 2026-11-26 — Preflight state rỗng, watchdog cũ không chạy, quota 16 vCPU, credit khoảng 76,94 USD, giá EC2 0,09576 USD/giờ; plan 5 create. Run `boot-82c3f91b4c2b`: user data tự cài, timer active, thử verify lúc RUNNING exit 1, sau đó READY. SHA nguồn `fb7ce454442dd92bcaa981d857f77645ccccd921`; verify smoke exit 0, report passed 8 checks. Tải evidence qua SSM, xác minh checksum; destroy 5 tài nguyên, xác nhận instance terminated, volume/security group và IAM role/profile không còn, state rỗng và watchdog đã thoát.
- 2026-11-26 — Người yêu cầu xác nhận review với vai trò đại diện nhóm và yêu cầu chuyển REVIEW sang DONE; kiểm tra lại hai archive evidence, test Bash 8 passed, suite nhẹ 233 passed/13 skipped/67 deselected, Terraform validate/fmt, Ruff và diff check đạt.
- 2026-11-26 — Rà soát hoàn thành: ghi [BL-THANH-43](../backlog.md#trọng) cho Trọng vì README gốc/kiến trúc/data-flow chưa theo kịp code LIVE và serving; giữ lịch sử review trong tài liệu của các owner.

## Kết quả

Kiểm thử trên Windows: `$env:DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -m 'not integration and not spark'` → 233 passed, 13 skipped (5 POSIX bootstrap cũ, 8 test Bash mới), 67 deselected. Test Bash mới trên Linux container: `docker run --rm --mount "type=bind,src=<repo>,dst=/workspace" -w /workspace wikipulse-spark:0.1.0 python -m pytest ingestion/collector/tests/test_ec2_verify.py -q -p no:cacheprovider` → 8 passed. `terraform fmt -check`, `terraform validate`, `ruff check ingestion/collector`, `git diff --check` đạt; user data render khoảng 3168 bytes.

EC2 thật AL2023 x86-64: Terraform apply nhúng script từ working tree, checkout sạch SHA trên GitHub; gọi `wikipulse-verify` không cài tay → REPLAY smoke passed, Bronze 11/invalid 2/Silver 7/Gold 2. Log bootstrap và report/log smoke tại `artifacts/final-checker-20261126/ec2-bootstrap-evidence.tar.gz` (gitignored), SHA-256 `8d4e05cc4d01e359994fc7d66ba053cabdc60b4fbce82d0d3c53d5e522fefad6`. Chi phí thực tế do AWS cập nhật sau, không suy từ ước tính. Lệnh vận hành và giới hạn ở [README Terraform](../../ingestion/collector/terraform/README.md).
