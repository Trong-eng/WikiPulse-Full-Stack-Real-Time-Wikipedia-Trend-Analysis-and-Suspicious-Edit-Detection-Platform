# Collector LIVE — Thành

Collector nhận Wikimedia EventStreams SSE và gửi raw topic Kafka bằng envelope chung với replay. `PIPELINE_MODE=LIVE` là bắt buộc. Dữ liệu raw giữ payload nguồn và có thể chứa username/IP; không ghi payload hoặc SSE ID vào log.

Từ repo root, bật Docker Desktop và dùng một Compose project/run riêng. Ví dụ PowerShell (chọn project và cổng không trùng môi trường khác):

```powershell
$env:COMPOSE_PROJECT_NAME = 'wikipulse-live-demo'
$env:PIPELINE_MODE = 'LIVE'
$env:RUN_ID = 'live-demo'
docker compose --profile live up -d --build collector
docker compose --profile live logs --tail=100 collector
```

`PIPELINE_MODE`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_RAW_TOPIC`, `COLLECTOR_VERSION` và `WIKIMEDIA_STREAM_URL` được lấy từ môi trường. URL mặc định là Wikimedia recentchange; User-Agent mô tả có link repo. Collector dùng timeout kết nối 10 giây, đọc 60 giây, Kafka `acks=all`, tối đa 100 future chờ, poll ACK và ghi counters định kỳ 30 giây. HTTP 4xx trừ 408/429 là lỗi cấu hình/nguồn không tự phục hồi; 408/429, 5xx và lỗi kết nối được retry với backoff có jitter tối đa 60 giây.

Log `counters` gồm `received`, `published`, `publish_failed`, `parse_errors`, `reconnects`, `last_event_time`. `published` đếm ACK thành công trong tiền tố liên tiếp đã xử lý; trong khi có ACK ngoài thứ tự con số có thể trễ. `parse_errors` tính JSON sai hoặc không phải object; những payload này vẫn được gửi nguyên văn để downstream phân loại. Đây là số theo tiến trình, không phải số duy nhất hay thống kê toàn hệ thống.

Vị trí resume chỉ tiến sau ACK liên tiếp thành công; sự kiện sau ACK lỗi có thể được gửi lại. SSE ID được giữ opaque. Nếu nguồn không cung cấp ID phù hợp hoặc không còn lưu vị trí, resume không bảo đảm đầy đủ. Cursor chỉ ở bộ nhớ: restart tiến trình/container bắt đầu từ stream hiện tại. Không cam kết exactly-once hoặc khôi phục qua restart; delivery và giới hạn watermark chờ nhóm chốt trong backlog.

SIGTERM/SIGINT ngừng nhận mới và đợi ACK/flush có giới hạn; lỗi chưa xác nhận được báo exit khác 0. Compose mặc định chỉ đợi 10 giây, nên dừng collector trước bằng `docker compose --profile live stop -t 100 collector`; sau đó `docker compose --profile live down` giữ volume. Chỉ xóa volume nếu đã xác định đúng project test và chủ động cần dọn.

Test không cần cluster:

```powershell
.\.venv\Scripts\python.exe -m pytest ingestion/collector/tests ingestion/tests replay/tests -q -m 'not integration'
```

Recording dự phòng là tùy chọn khi chạy collector local từ repo root:

```powershell
$env:PIPELINE_MODE = 'LIVE'
.\.venv\Scripts\python.exe -m ingestion.collector.app.main --record artifacts/recordings/demo.jsonl
```

Đường dẫn phải nằm trong `artifacts/recordings/`, không được tồn tại trước và không qua
symlink/junction. Chỉ event đã ACK liên tiếp được ghi; JSON lỗi hoặc không phải object bị bỏ khỏi
recording. User được thay bằng định danh giả ổn định trong một lần chạy; comment nguồn bị loại,
thay bằng `Reverted` khi khớp heuristic. Các trường cấu trúc khác (bao gồm metadata và title) giữ
giá trị nguồn; title theo yêu cầu được giữ nguyên và có thể chứa username/IP. File chỉ dùng local,
không commit trước khi Thành xử lý và kiểm tra quyền riêng tư. Recording không phải bản sao hoàn
chỉnh hay ẩn danh hoàn toàn; lỗi ghi làm collector dừng với mã lỗi. Muốn giữ file khi chạy trong
container phải bind-mount thư mục `artifacts/recordings` của host vào `/workspace/artifacts/recordings`.

Test integration dùng Kafka riêng, broker có thể truy cập từ host (test tạo/xóa một topic UUID của chính nó, SSE giả cục bộ):

```powershell
$env:WIKIPULSE_TEST_KAFKA = '127.0.0.1:29092'
.\.venv\Scripts\python.exe -m pytest ingestion/collector/tests/test_kafka_integration.py -q
```

Không dùng broker hoặc dữ liệu production cho integration test. Evidence và trạng thái nghiệm thu ở [plan W2](../../docs/plans/W2-THANH-01.md).

## EC2 nghiệm thu tạm bằng Terraform

Cấu hình `ingestion/collector/terraform/` tạo một EC2 `m7i-flex.large` ở `us-east-2`, ổ gp3
30 GiB và role SSM; không mở inbound. Máy tự yêu cầu terminate sau 3 giờ khi timer hoạt động.
Tài nguyên có thể tiêu thụ credit hoặc phát sinh phí; trước mỗi lượt kiểm tra AWS Free Tier,
giá hiện hành và trần ngân sách. Không dùng cấu hình này để vận hành production.

Terraform state/plan được đặt trong `artifacts/terraform/w4/` (Git bỏ qua). Chỉ chạy một lượt
tại một thời điểm; không xóa state khi còn tài nguyên. Từ repo root trên PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path artifacts/terraform/w4 | Out-Null
$taskRoot = (Get-Location).Path
$env:TF_DATA_DIR = (Resolve-Path artifacts/terraform/w4).Path + '\tfdata'
$taskRunId = 'run-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
Set-Content -LiteralPath artifacts/terraform/w4/run-id.txt -Value $taskRunId
terraform -chdir=ingestion/collector/terraform init -input=false
terraform -chdir=ingestion/collector/terraform validate
$taskPlan = (Resolve-Path artifacts/terraform/w4).Path + '\w4.tfplan'
terraform -chdir=ingestion/collector/terraform plan -input=false "-var=run_id=$taskRunId" "-out=$taskPlan"
```

Kiểm tra plan chỉ tạo tài nguyên của lượt này, AMI, subnet, route Internet, chi phí dự kiến và
credit trước khi apply. Để có lớp dự phòng khi phiên điều khiển bị gián đoạn, chạy watchdog ẩn
ngoài sandbox có quyền gọi Terraform/AWS, sau đó apply saved plan:

```powershell
$taskWatchdog = Join-Path $taskRoot 'ingestion/collector/terraform/watchdog.ps1'
$taskProc = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"' + $taskWatchdog + '"'),
  '-RepoRoot',('"' + $taskRoot + '"'),'-RunId',$taskRunId)
Get-Process -Id $taskProc.Id
terraform -chdir=ingestion/collector/terraform apply -input=false $taskPlan
if ($LASTEXITCODE -ne 0) { throw 'Apply failed; retain state and run cleanup.' }
$taskInstance = terraform -chdir=ingestion/collector/terraform output -raw instance_id
$taskVolumes = (aws ec2 describe-instances --region us-east-2 --instance-ids $taskInstance --query 'Reservations[0].Instances[0].BlockDeviceMappings[].Ebs.VolumeId' --output text) -split '\s+'
```

Xác nhận SSM online và `systemctl is-active wikipulse-expire.timer` trên instance; timer và
watchdog là cơ chế dự phòng, không phải giới hạn chi phí cứng. Sau nghiệm thu, luôn dọn đúng
state/run đã tạo, kể cả khi test thất bại:

```powershell
terraform -chdir=ingestion/collector/terraform destroy -auto-approve -input=false "-var=run_id=$taskRunId"
if ($LASTEXITCODE -ne 0) { throw 'Destroy failed; keep watchdog running and state intact.' }
$taskRemaining = terraform -chdir=ingestion/collector/terraform state list
if ($LASTEXITCODE -ne 0 -or $taskRemaining) { throw 'State not empty; keep watchdog running.' }
$taskStatus = aws ec2 describe-instances --region us-east-2 --instance-ids $taskInstance --query 'Reservations[0].Instances[0].State.Name' --output text
if ($LASTEXITCODE -ne 0 -or $taskStatus -ne 'terminated') { throw 'Instance not terminated.' }
foreach ($taskVolume in $taskVolumes) {
  $taskCount = aws ec2 describe-volumes --region us-east-2 --filters "Name=volume-id,Values=$taskVolume" --query 'length(Volumes)' --output text
  if ($LASTEXITCODE -ne 0 -or $taskCount -ne '0') { throw 'Volume still exists; keep watchdog running.' }
}
New-Item -ItemType File -Force -Path "artifacts/terraform/w4/$taskRunId.stop" | Out-Null
Wait-Process -Id $taskProc.Id -ErrorAction SilentlyContinue
```

Chỉ tạo file dừng watchdog sau khi đã xác nhận instance terminated và tài nguyên của lượt này
đã xóa; kiểm tra thêm security group, IAM role và instance profile theo tên lượt. Phải đợi
watchdog thoát trước khi bắt đầu lượt mới vì state dùng chung. Nếu apply thất bại trước khi có
output, giữ state và dùng `terraform state list` / `terraform state show` để tìm tài nguyên đã
tạo, lưu ID instance và volume trước khi destroy rồi xác minh qua AWS; có thể không có instance
hoặc volume nếu apply thất bại sớm. Không ghi output state chứa thông tin nhạy cảm vào repo.
Nếu thao tác bị lỗi, giữ state để khôi phục/dọn; EBS còn tồn tại có thể vẫn tính phí.
