# EC2 tạm cho WikiPulse REPLAY

Terraform tạo EC2 Amazon Linux 2023, role SSM, security group không inbound và ổ gp3 30 GB. User data kích hoạt timer terminate sau 3 giờ, cài Git, Docker, Compose và Python, clone đúng SHA và tạo venv. Trạng thái bootstrap nằm ở `/var/lib/wikipulse/status` (`RUNNING`, `READY`, `FAILED`); log tại `/var/log/wikipulse-bootstrap.log`. User data chạy một lần khi tạo EC2. `apply` kết thúc không có nghĩa bootstrap đã xong.

Trên EC2, sau khi `READY`, `sudo wikipulse-verify` kiểm tra SHA/checkout và chạy REPLAY smoke có build image, dùng project riêng. Smoke in đường dẫn `Evidence:` chứa `report.json`, `commands.log`, `services.log`. Nếu trạng thái chưa `READY`, xem log; lệnh verify thoát lỗi, không tự chờ hay tự cài lại. Thời gian ba giờ bắt đầu khi EC2 khởi động; timer và watchdog chỉ là dự phòng, không phải giới hạn chi phí cứng.

## Tạo EC2 từ Windows PowerShell

Yêu cầu Terraform >=1.5, AWS CLI, quyền EC2/IAM/SSM, VPC/subnet mặc định và internet. Xác minh account, quyền, quota, giá, credit, ngân sách và Terraform state trước mỗi lượt. Chỉ chạy một lượt tại một thời điểm; không ghi đè state còn tài nguyên. SHA phải có trên GitHub; script bootstrap/verify được Terraform nhúng từ workspace, độc lập với nội dung checkout.

```powershell
New-Item -ItemType Directory -Force -Path artifacts/terraform/w4 | Out-Null
$taskRoot = (Get-Location).Path
$env:TF_DATA_DIR = (Resolve-Path artifacts/terraform/w4).Path + '\tfdata'
$taskRunId = 'run-' + [guid]::NewGuid().ToString('N').Substring(0,12)
$taskRevision = (git rev-parse HEAD).Trim()
Set-Content -LiteralPath artifacts/terraform/w4/run-id.txt -Value $taskRunId
Set-Content -LiteralPath artifacts/terraform/w4/source-revision.txt -Value $taskRevision
terraform -chdir=ingestion/collector/terraform init -input=false
terraform -chdir=ingestion/collector/terraform validate
terraform -chdir=ingestion/collector/terraform state list
$taskPlan = (Resolve-Path artifacts/terraform/w4).Path + '\w4.tfplan'
terraform -chdir=ingestion/collector/terraform plan -input=false "-var=run_id=$taskRunId" "-var=source_revision=$taskRevision" "-out=$taskPlan"
```

Kiểm tra saved plan chỉ tạo tài nguyên của lượt này. Khởi động watchdog ẩn và apply:

```powershell
$taskWatchdog = Join-Path $taskRoot 'ingestion/collector/terraform/watchdog.ps1'
$taskProc = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"' + $taskWatchdog + '"'),
  '-RepoRoot',('"' + $taskRoot + '"'),'-RunId',$taskRunId,'-SourceRevision',$taskRevision)
Get-Process -Id $taskProc.Id
terraform -chdir=ingestion/collector/terraform apply -input=false $taskPlan
if ($LASTEXITCODE -ne 0) { throw 'Apply failed; retain state and run cleanup.' }
$taskInstance = terraform -chdir=ingestion/collector/terraform output -raw instance_id
$taskVolumes = (aws ec2 describe-instances --region us-east-2 --instance-ids $taskInstance --query 'Reservations[0].Instances[0].BlockDeviceMappings[].Ebs.VolumeId' --output text) -split '\s+'
aws ssm start-session --region us-east-2 --target $taskInstance
```

Session Manager CLI cần plugin AWS tương ứng; cũng có thể mở Session Manager trong AWS Console. Sau khi SSM online, trên EC2:

```bash
sudo cat /var/lib/wikipulse/status
sudo systemctl is-active wikipulse-expire.timer
sudo tail -n 50 /var/log/wikipulse-bootstrap.log
sudo wikipulse-verify
```

Chạy verify sau khi `READY`. Lưu exit code và report/log được in trong output; `passed` và exit code 0 là điều kiện đạt. Verify chỉ kiểm REPLAY core, không tự chạy LIVE/HDFS. File ở `/opt/wikipulse/artifacts/` biến mất khi terminate.
Nếu kết nối quá sớm trước khi lệnh verify được cài, kiểm tra `/var/log/cloud-init-output.log` và chờ user data bắt đầu.

Để chuyển evidence qua phiên SSM mà không mở inbound, trên EC2 đóng gói đúng thư mục smoke vừa chạy rồi chia base64 thành các phần ngắn (thay đường dẫn bằng giá trị `Evidence:`):

```bash
sudo tar -C /opt/wikipulse/artifacts -czf /tmp/wikipulse-evidence.tar.gz 'smoke-<run-id>'
sudo sha256sum /tmp/wikipulse-evidence.tar.gz
sudo sh -c 'base64 -w0 /tmp/wikipulse-evidence.tar.gz | split -b 9000 - /tmp/wikipulse-evidence.part-'
sudo ls /tmp/wikipulse-evidence.part-*
sudo cat /tmp/wikipulse-evidence.part-*
```

Sao chép các phần base64 theo thứ tự, nối nguyên vẹn vào file `evidence.b64` trên máy điều khiển, giải mã và so sánh SHA-256 với output trên EC2 trước khi dọn. Không commit payload LIVE, credentials hoặc Terraform state. Nếu dùng S3/Run Command để chuyển thay thế, cấu hình quyền và nơi lưu phù hợp trước khi xóa máy.

```powershell
$taskEncoded = Get-Content -LiteralPath evidence.b64 -Raw
$taskEvidence = Join-Path (Get-Location).Path 'wikipulse-evidence.tar.gz'
[System.IO.File]::WriteAllBytes($taskEvidence, [Convert]::FromBase64String($taskEncoded))
Get-FileHash -LiteralPath $taskEvidence -Algorithm SHA256
```

## Dọn tài nguyên

Sau khi lưu evidence, luôn dọn đúng run/state, kể cả khi bootstrap/verify thất bại:

```powershell
terraform -chdir=ingestion/collector/terraform destroy -auto-approve -input=false "-var=run_id=$taskRunId" "-var=source_revision=$taskRevision"
if ($LASTEXITCODE -ne 0) { throw 'Destroy failed; keep watchdog running and state intact.' }
$taskRemaining = terraform -chdir=ingestion/collector/terraform state list
if ($LASTEXITCODE -ne 0 -or $taskRemaining) { throw 'State not empty; keep watchdog running.' }
$taskStatus = aws ec2 describe-instances --region us-east-2 --instance-ids $taskInstance --query 'Reservations[0].Instances[0].State.Name' --output text
if ($LASTEXITCODE -ne 0 -or $taskStatus -ne 'terminated') { throw 'Instance not terminated.' }
foreach ($taskVolume in $taskVolumes) {
  $taskCount = aws ec2 describe-volumes --region us-east-2 --filters "Name=volume-id,Values=$taskVolume" --query 'length(Volumes)' --output text
  if ($LASTEXITCODE -ne 0 -or $taskCount -ne '0') { throw 'Volume still exists; keep watchdog running.' }
}
$taskName = "wikipulse-thanh-w4-$taskRunId"
$taskGroups = aws ec2 describe-security-groups --region us-east-2 --filters "Name=group-name,Values=$taskName" --query 'length(SecurityGroups)' --output text
if ($LASTEXITCODE -ne 0 -or $taskGroups -ne '0') { throw 'Security group remains or check failed.' }
$taskRoleCheck = aws iam get-role --role-name $taskName 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -or $taskRoleCheck -notmatch 'NoSuchEntity') { throw 'IAM role check failed or role still exists.' }
$taskProfileCheck = aws iam get-instance-profile --instance-profile-name $taskName 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -or $taskProfileCheck -notmatch 'NoSuchEntity') { throw 'IAM profile check failed or profile still exists.' }
New-Item -ItemType File -Force -Path "artifacts/terraform/w4/$taskRunId.stop" | Out-Null
Wait-Process -Id $taskProc.Id -ErrorAction SilentlyContinue
```

Hai lệnh IAM chỉ coi `NoSuchEntity` là đã xóa; lỗi quyền hoặc mạng không chứng minh đã xóa. Nếu apply lỗi trước khi có output, giữ state, dùng `terraform state list`/`state show` xác định tài nguyên đã tạo và ID trước destroy; có thể chưa có instance hay volume. Không dừng watchdog đến khi đã xác nhận dọn xong. Chờ watchdog thoát trước lượt mới vì state dùng chung.
