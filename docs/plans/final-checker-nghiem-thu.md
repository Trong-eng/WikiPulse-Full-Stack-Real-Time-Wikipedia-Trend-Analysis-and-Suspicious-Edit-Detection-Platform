Trạng thái: DONE · Owner: Final-Checker · Reviewer: Cả nhóm (người yêu cầu đại diện xác nhận) · Liên quan: CP0, CP1, CP2, CP3, CP4

## Mục tiêu

Đối chiếu và nghiệm thu các checkpoint toàn nhóm trên phiên bản ứng viên, với evidence tái hiện được; không suy DONE từ nhãn trạng thái.

## Phạm vi / Không làm

Kiểm tra mã, cấu hình, tests, REPLAY, HDFS, LIVE, phục hồi và evidence máy thứ hai. Final-Checker không tự xác nhận thay owner/reviewer, không sửa module thuộc owner khác, không commit/push.

## Các bước

- [x] Chốt SHA, working tree, môi trường và đối chiếu evidence từng CP.
- [x] Chạy unit, lint, Compose, Spark, integration và smoke REPLAY/HDFS cô lập.
- [x] Kiểm tra LIVE ≥15 phút, UI/API, privacy và phục hồi với evidence tổng hợp.
- [x] Đối chiếu máy thứ hai, reviews, cập nhật phát hiện cho đúng owner và bàn giao từng CP.
- [x] Kiểm tra account, state/watchdog, quota, giá và giới hạn dự kiến 5 USD; tạo EC2 test qua Terraform/SSM.
- [x] Cài môi trường trên EC2, clean clone SHA ứng viên, chạy REPLAY smoke và chuyển evidence về workspace.
- [x] Xác nhận dọn tài nguyên AWS và đối chiếu toàn bộ điều kiện CP4; cập nhật kết quả theo evidence.

## Quyết định

- Dùng evidence máy thứ hai hiện có nếu chứng minh được tiêu chí và phiên bản ứng viên; thiếu evidence thì không tuyên bố CP4 đạt.
- Docker test dùng namespace và volume riêng; không thay đổi dữ liệu dev hoặc commit payload LIVE.
- Ngày 2026-11-26 người yêu cầu xác nhận đã nghiệm thu và đại diện các reviewer chéo xác nhận phần review, nghiệm thu nhóm. Đây là xác nhận của người yêu cầu, không phải bản ghi review riêng từ từng thành viên và không thay thế evidence chạy máy thứ hai.

## Nhật ký

- 2026-11-26 — Bắt đầu triển khai kế hoạch EC2 theo yêu cầu; trần chi phí dự kiến 5 USD; giữ evidence và state của lượt cũ.
- 2026-11-26 — Preflight: account FREE ACTIVE, credit khoảng 76,94 USD; Terraform state W4 rỗng, không thấy watchdog PowerShell cũ, subnet mặc định có route internet; quota EC2 standard 16 vCPU. Một EC2 khác đang chạy được giữ nguyên. AWS Pricing: m7i-flex.large Ohio 0,09576 USD/giờ, gp3 0,08 USD/GB-tháng; IPv4 khoảng 0,005 USD/giờ. Ước tính 3 giờ compute + IPv4 + 30 GB gp3 khoảng 0,31 USD trước transfer/thuế, dưới 5 USD; kiểm soát phát sinh và dọn sớm.
- 2026-11-26 — Terraform plan 5 create, không thay đổi/xóa; tạo EC2 riêng, SSM online và timer active, watchdog dự phòng chạy. Cài đầu tiên lỗi vì `curl` xung đột `curl-minimal`; cài lại dùng curl sẵn có thành công. AL2023 x86-64, 7779 MiB RAM, Git 2.50.1, Python 3.11.18, Docker 25.0.18, Compose 2.39.4 (checksum OK). Clone trực tiếp GitHub và checkout SHA `fb7ce454442dd92bcaa981d857f77645ccccd921`; smoke đang chạy.
- 2026-11-26 — Bắt đầu nghiệm thu với vai trò Final-Checker theo yêu cầu; HEAD `fb7ce454442dd92bcaa981d857f77645ccccd921`, có các thay đổi tài liệu sẵn có được giữ nguyên.
- 2026-11-26 — Suite nhẹ lần đầu 231 passed, 2 failed do Docker Compose CLI; chạy lại với `DOCKER_CONFIG` theo `thanh-dashboard-recheck` được 233 passed, 5 skipped, 67 deselected. Ruff và Compose config core/full đạt.
- 2026-11-26 — REPLAY smoke local và HDFS đều `passed`; HDFS giữ dữ liệu và 9 checkpoint qua recreate. Spark suite trong container: 68 passed. Acceptance HDFS chuyên biệt đang chạy.
- 2026-11-26 — Acceptance HDFS chuyên biệt 7/7 pha đạt, 9 checkpoint giữ danh tính. Kafka integration và outage/recovery mỗi bài 1 passed; Cassandra thật 8 passed, 72 deselected; các project/container test riêng đã dọn.
- 2026-11-26 — LIVE bắt đầu `03:23:32Z`; mẫu `03:28:51Z` collector running, published 9271, received 9273, reconnects 1, parse/publish failures 0. Mẫu API có dữ liệu 4 loại, không thấy các tên trường nhạy cảm được quét; AppTest bốn trang không exception/error. Chưa kết luận đủ 15 phút.
- 2026-11-26 — Stack REPLAY analytics Cassandra riêng: API có activity/trends/suspicious/event; bốn trang AppTest không lỗi. Tắt API: bốn trang hiện lỗi, không exception; bật API: healthy và bốn AppTest mới không lỗi. Phạm vi không chứng minh phục hồi trên cùng phiên browser.
- 2026-11-26 — Catchup Spark: 1.200 sự kiện tổng hợp, ba query Kafka tới offset đích sau 9,11 giây, 1 passed; recording tổng hợp qua Spark 1 passed. Năm test bootstrap POSIX skip trên Windows, HDFS smoke đã kiểm bootstrap trong Linux container.
- 2026-11-26 — LIVE mẫu `03:36:45Z`: collector running, restart count 0, published 22144, received 22145, reconnects 1, parse/publish failures 0; mẫu bốn trang và bốn API tiếp tục có dữ liệu, không phát hiện tên trường nhạy cảm được quét. `w32tm /query /status` bị từ chối; ba mẫu stripchart `time.windows.com` khoảng +1,908–1,909 giây, không chứng minh đồng bộ đồng hồ.
- 2026-11-26 — LIVE mẫu cuối `03:38:39Z`, sau ít nhất 15 phút 06 giây từ StartedAt `03:23:32Z`: collector running, restart 0, received 25330, published 25327, reconnect 1, parse/publish failures 0; bốn API có dữ liệu và AppTest bốn trang không lỗi. Đây là counters prefix, không chứng minh không mất/trùng; UI được lấy mẫu, không giám sát liên tục. Đã stop collector và dọn project riêng.
- 2026-11-26 — Người yêu cầu xác nhận đã nghiệm thu xong và đại diện từng reviewer chéo xác nhận review, nghiệm thu nhóm; còn kiểm chứng clean clone/REPLAY trên máy thứ hai đúng SHA ứng viên.
- 2026-11-26 — EC2 clean clone trực tiếp GitHub tại `fb7ce454442dd92bcaa981d857f77645ccccd921`; `git status --porcelain=v1` rỗng trước venv. Cài `.[dev]` và `dashboard/requirements.txt`, chạy `PYTHONUTF8=1 .venv/bin/python scripts/smoke_test.py`: exit 0, report `passed`, 8 checks; Bronze 11, invalid 2, Silver 7, Gold target 2, 9 query ready. Chuyển archive về workspace qua SSM và đối chiếu SHA-256 thành công.
- 2026-11-26 — `terraform destroy` 5 tài nguyên; AWS xác nhận instance terminated, volume/security group không còn, IAM role/profile NoSuchEntity, Terraform state rỗng. Sau xác nhận, tạo stop signal và đợi watchdog thoát. Các tài nguyên khác của account không bị thay đổi.

## Kết quả

Evidence local (gitignored): `artifacts/smoke-20261126030846-6e56d0c9d5604ca9bcc1044612438878/report.json`, `artifacts/smoke-20261126031128-b4ae22ebe4eb47bfbe2301d10dc07e4f/report.json`, `artifacts/w3-20261126031620-1a17075fc6e2/report.json`. Lệnh: `.venv\Scripts\python.exe scripts\smoke_test.py` và cùng lệnh thêm `--hdfs --no-build`; `docker compose -p wikipulse-finalcheck-spark run --rm --no-deps spark python -m pytest processing/spark/tests -q`; `.venv\Scripts\python.exe -m processing.spark.acceptance.run_hdfs --no-build`. Integration theo README module, với broker và Cassandra riêng. LIVE/UI theo quy trình [thanh-dashboard-recheck](thanh-dashboard-recheck.md#cách-kiểm-tra-lại-replay-và-live-trên-bản-clone-sạch); script lấy mẫu local `artifacts/final-checker-20261126/run_stack.py` kế thừa từ lượt đó, không lưu payload.

| Cổng | Đối chiếu của Final-Checker |
|---|---|
| CP0 | Smoke REPLAY hiện tại đạt các kiểm tra core và fixture; cần owner nghiệm thu. |
| CP1 | Có evidence chạy CP0 của Thành trên Windows trong W1; các plan/backlog vẫn nêu review chéo còn thiếu, cần nhóm xác nhận. |
| CP2 | Fixture, LIVE, UI và HDFS có evidence mới; chưa thay review contract của producer/consumer và nghiệm thu nhóm. |
| CP3 | HDFS smoke và 7 pha acceptance đạt; serving Cassandra được kiểm tra riêng. Cần review nhóm, không suy kết quả test thành phê duyệt. |
| CP4 | Clean clone EC2 đúng SHA, REPLAY smoke passed, evidence LIVE ≥15 phút và bốn trang lấy mẫu trên cùng SHA, xác nhận review/nghiệm thu đại diện đã ghi; các điều kiện checkpoint đã được đối chiếu. |

Các nhận xét về review còn thiếu trong bảng phản ánh trạng thái trước xác nhận ngày 2026-11-26 ở mục Quyết định. Người yêu cầu đã xác nhận review và nghiệm thu nhóm với vai trò đại diện. Không commit/push.

### Evidence clean clone EC2

Terraform run `cp4-465fb96beea1`, EC2 AL2023 x86-64, 2 vCPU/7779 MiB RAM, Python 3.11.18, Git 2.50.1, Docker 25.0.18, Compose 2.39.4; instance đã terminate. Lệnh chính trên máy: `git clone https://github.com/Trong-eng/WikiPulse-Full-Stack-Real-Time-Wikipedia-Trend-Analysis-and-Suspicious-Edit-Detection-Platform.git source`, `git checkout --detach fb7ce454442dd92bcaa981d857f77645ccccd921`, `git rev-parse HEAD`, `git status --porcelain=v1`, `python3.11 -m venv .venv`, `.venv/bin/python -m pip install -e '.[dev]' -r dashboard/requirements.txt`, `PYTHONUTF8=1 .venv/bin/python scripts/smoke_test.py`. Report local và log được đóng gói tại `artifacts/final-checker-20261126/ec2-cp4-evidence.tar.gz` (gitignored), SHA-256 `2e787baac3818408681d7e7dcae26993887421a9c9ce3d225cffbd3b82f3e77a`; archive chứa `head.txt`, `clean-status.txt`, `smoke-exit.txt`, report, commands/services logs. Có thể đọc lại bằng `python -m tarfile -l artifacts/final-checker-20261126/ec2-cp4-evidence.tar.gz` và `Get-FileHash artifacts/final-checker-20261126/ec2-cp4-evidence.tar.gz -Algorithm SHA256`.
