Trạng thái: REVIEW · Owner: Thành · Reviewer: Trọng · Liên quan: W4-THANH-01, W2-THANH-01, W3-THANH-01, CP3/CP4

## Mục tiêu

Kiểm thử, sửa lỗi ảnh hưởng demo, chạy LIVE ≥30 phút trên máy thứ hai và bàn giao ingestion/replay. Lộ trình: [Thành](thanh-ingestion-4-tuan.md).

## Phạm vi / Không làm

Ingestion/replay, test và Terraform EC2 nghiệm thu tạm trong phạm vi Thành. Giữ W2/W3 chưa commit; không tự commit/push, không sửa module owner khác. LIVE giữ username/ID nguồn trong Kafka/Bronze; không commit dữ liệu danh tính. Recording giữ cách W3. AWS FREE plan, region us-east-2, chi phí dự kiến tối đa 5 USD/lượt; dọn tài nguyên test.

## Các bước

- [x] Pha 1: baseline, rà soát lỗi ảnh hưởng demo, subagent review.
- [x] Pha 2: Terraform EC2 cô lập, giá/plan, subagent review trước khi tạo.
- [x] Pha 3: snapshot, smoke và LIVE ≥30 phút trên EC2, subagent review.
- [x] Pha 4: cleanup AWS, runbook, regression và bàn giao, subagent review.

## Quyết định

- EC2 m7i-flex.large 8 GiB, gp3 30 GiB, SSM, không ingress, không NAT/EIP. Credit FREE còn $83,568613 tại thời điểm bắt đầu; giá EC2 Ohio $0,09576/giờ trước credit. Trần dự kiến $5/lượt.
- Snapshot làm từ working tree đã sửa, xác minh manifest/hash: không gọi là clean clone theo SHA. W2/W3 vẫn REVIEW; không tự đóng CP3/CP4.
- Mỗi pha được review bởi subagent; không tự gửi tin nhắn cho thành viên nhóm.

## Nhật ký

- 2026-11-23 — Bắt đầu W4, giữ các thay đổi W2/W3; AWS account FREE ACTIVE, mặc định us-east-2.
- 2026-11-23 — Baseline 180 passed, 5 skipped, 63 deselected; recording Spark 1 passed; lint/diff check exit 0. Review tái hiện timestamp biên gây vòng reconnect: thêm test RED→GREEN, bỏ qua overflow khi cập nhật counter, vẫn gửi event.
- 2026-11-23 — Terraform validate và saved plan: 5 create, 0 change/destroy; review cảnh báo timer best-effort và route subnet. Đã xác nhận route IGW, SSM online, timer active, watchdog ẩn độc lập, 7.779 MiB RAM/28.814 MiB trống; dùng image AL2023 x86_64 và m7i-flex.large trong us-east-2.
- 2026-11-23 — Snapshot 122 file, base `0c59b034ea48dc5b04131ae575eed1bf748d86da`, tar SHA-256 `da67f470381197c33b576bea832c6e2ac2602ccc448fa9a88304b6637bc328e7`; đối chiếu trên EC2 0 mismatch. Docker 25.0.14, Compose 2.39.4; smoke REPLAY core `status=passed`, 8 checks, đã xác nhận project/volume smoke không còn. LIVE bắt đầu 10:08:39 UTC, đang theo dõi; SSE ngắt/nối có kiểm soát ghi 4 reconnect, Kafka stop/start đã thực hiện.
- 2026-11-23 — LIVE dừng 10:39:24 UTC, exit 0: received/published 70.252/70.252, tổng Kafka end-offset 70.252, 5 reconnect, 0 restart/parse error/publish failure. Review pha 3 xác nhận không suy ra exactly-once, LIVE end-to-end tới dashboard, hoặc CP3/CP4; Kafka stop 15 giây không phát sinh publish failure nên không chứng minh nhánh retry.
- 2026-11-23 — `terraform destroy`: 5 destroyed; AWS xác nhận instance terminated, volume/security group/role/profile không còn và Terraform state rỗng. Đã gửi tín hiệu dừng watchdog. Regression 181 passed, 5 skipped, 63 deselected; Ruff, `git diff --check` và `terraform fmt -check` thành công.
- 2026-11-23 — Review pha 4 phát hiện nguy cơ watchdog cũ dọn state của lượt mới: thêm kiểm tra state theo run ID và tín hiệu dừng trước destroy, đợi process thoát, cố định region trong runbook. Review lại không thấy lỗi nghiêm trọng qua đọc tĩnh. Watchdog lưu trong repo mới được kiểm tra cú pháp, chưa được thử destroy thực tế; lượt này dùng watchdog riêng trong artifacts. Terraform validate thành công, watchdog đã chạy thực tế đã thoát.
- 2026-11-23 — Theo yêu cầu Thành, tách commit W2/W3/W4 và tích hợp các cập nhật serving mới từ `origin/main`: regression `-m 'not integration and not spark'` đạt 224 passed, 5 skipped, 67 deselected; Ruff, kiểm tra diff và Terraform fmt đạt. Việc merge không thay cho review contract của Linh hoặc demo phối hợp.

## Kết quả

- Chạy lại test: PowerShell đặt `$env:DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'`, rồi `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -m 'not integration and not spark' --tb=line`: 181 passed, 5 skipped, 63 deselected, 26 warnings. `.\.venv\Scripts\python.exe -m ruff check .`, `git diff --check`, `terraform fmt -check -recursive ingestion/collector/terraform`: thành công.
- Tạo/dọn môi trường: [runbook Terraform](../../ingestion/collector/README.md). Lần này dùng saved plan và `terraform -chdir=ingestion/collector/terraform destroy -auto-approve -input=false -no-color "-var=run_id=<run-id>"`; kiểm tra bổ sung bằng `terraform state list` và AWS CLI cho EC2, EBS, security group, IAM role/profile. Tài nguyên đã bị xóa; chi phí thực tế có thể cập nhật trễ trên AWS.
- Trên EC2 đã kiểm chứng smoke REPLAY core 8 checks và LIVE collector → Kafka 30 phút 44 giây. Các script thu thập và snapshot của lượt chạy lưu trong `artifacts/terraform/w4/` bị Git ignore, nên evidence trên không tự tái hiện từ clean clone; cần tự tạo lại snapshot sạch và thao tác SSM theo runbook khi thử lại. Smoke không chạy `--hdfs`. Tổng offset và counter không bảo đảm không mất/trùng dữ liệu. Chưa có demo LIVE với Mạnh hay review của các thành viên; W2/W3 vẫn REVIEW.
