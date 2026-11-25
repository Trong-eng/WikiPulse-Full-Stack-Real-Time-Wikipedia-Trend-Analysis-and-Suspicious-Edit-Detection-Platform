Trạng thái: DONE · Owner: Thành · Reviewer: Mạnh · Liên quan: W3-MANH-01, W4-MANH-01, BL-THANH-41

## Mục tiêu

Tái kiểm chứng những kết quả trong báo cáo dashboard/QA của Mạnh và cập nhật báo cáo theo evidence quan sát được.

## Phạm vi / Không làm

Được Thành yêu cầu sửa `docs/manh/dashboard-bao-cao.md`; không sửa code hay thay checkpoint/contract, không gửi hay commit dữ liệu LIVE chứa danh tính. Giữ thay đổi LaTeX chưa commit. Các bài thử dịch vụ dùng project và volume riêng, chỉ dọn tài nguyên của lượt đó.

## Các bước

- [x] Đối chiếu báo cáo, code, lệnh và môi trường; chạy lint, unit, config và kiểm đồng hồ.
- [x] Tái chạy smoke REPLAY/core và HDFS trên môi trường cô lập; kiểm UI/API, privacy và outage/recovery khi khả thi.
- [x] Chạy LIVE đủ thời gian và đo freshness nếu stack có thể sẵn sàng; chỉ lưu evidence tổng hợp, không ghi payload/định danh.
- [x] Cập nhật báo cáo Mạnh với nguồn, kết quả, điều kiện, giới hạn và các phần không tái hiện được; ghi lệnh và evidence ở plan này.

## Quyết định

- Không suy CP3/CP4 DONE từ một lần thử; không kết luận nguyên nhân timeout nếu chưa có evidence.
- Code liên quan owner khác chỉ được khảo sát; phát hiện chưa xử lý thì ghi rõ trong báo cáo, không tự sửa code.

## Nhật ký

- 2026-11-25 — Bắt đầu tái kiểm chứng theo yêu cầu Thành; Docker daemon chưa sẵn sàng tại lần kiểm tra đầu, quyền đọc trạng thái thời gian Windows bị từ chối trong sandbox.
- 2026-11-25 — Test dashboard 43 passed; suite nhẹ 233 passed/5 skipped/67 deselected, Ruff và hai Compose config đạt. `w32tm /query /status` báo dịch vụ chưa chạy; `w32tm /stripchart /computer:time.windows.com /samples:3 /dataonly` đo offset +1,440 đến +1,444 s, không thay giờ. Lượt smoke đầu lỗi buildx do DOCKER_CONFIG chỉ đọc; chạy lại với Docker config mặc định: smoke local passed, project riêng tự cleanup.
- 2026-11-25 — Dùng payload tổng hợp gọi hai validator suspicious/event: `user_hash` và `comment` bị từ chối, `username` và `ip` được validator chấp nhận; phép thử chỉ kiểm validator, không suy ra UI hiển thị các trường này. Smoke HDFS passed; REPLAY, outage và LIVE được kiểm tra trong stack riêng, đã dọn volume của từng lượt.
- 2026-11-25 — Cập nhật báo cáo theo evidence, mở BL-THANH-41 cho khác biệt evidence ở plan W4; không thay trạng thái checkpoint hay plan của Mạnh.

## Kết quả

Môi trường Windows, Python 3.12.7, Docker Engine 29.8.1, bộ nhớ Docker 16,6 GB; code `b4c7f57` (working tree còn các thay đổi tài liệu khác). Các lệnh chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pytest dashboard/tests -q -p no:cacheprovider
$env:DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -m 'not integration and not spark' --tb=line
.\.venv\Scripts\ruff.exe check .
docker compose config -q
docker compose --profile full config -q
w32tm /query /status
w32tm /stripchart /computer:time.windows.com /samples:3 /dataonly
Remove-Item Env:DOCKER_CONFIG
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\smoke_test.py
.\.venv\Scripts\python.exe scripts\smoke_test.py --hdfs --no-build
```

Kết quả lần lượt: `43 passed`; `233 passed, 5 skipped, 67 deselected`; Ruff và config đạt; Windows Time chưa chạy, ba mẫu offset `+1,4441462`, `+1,4403393`, `+1,4412976` giây; smoke local và HDFS `passed` (8 và 9 checks). `DOCKER_CONFIG` ở trên giúp suite tìm plugin Compose trên Windows; lệnh smoke dùng config mặc định để buildx có thể ghi state. Các file `artifacts/smoke-20261125140418-b52080d213d441feaef9634d20e74230/report.json` và `artifacts/smoke-20261125140750-cb82a4b701f14a5182d1c9b36bfd4145/report.json` là evidence local bị gitignore, không có trong bản clone sạch.

Kiểm thử dịch vụ dùng project/volume độc lập, `SPARK_ANALYTICS_SINK=cassandra`, cổng host cấp động; REPLAY nạp fixture và kiểm `/api/v1/activity`, `/trends`, `/suspicious-edits`, `/events/{id}`, sau đó chạy `streamlit.testing.v1.AppTest` lần lượt 4 trang; dừng rồi khởi động API để thử outage/recovery. LIVE đặt `PIPELINE_MODE=LIVE`, chạy collector cùng API, Spark, dashboard và cùng các dependency. Script điều phối tạm tại `artifacts/manh-recheck/run_stack.py` bị gitignore, không phải tài liệu có trong bản clone sạch; code và lệnh dịch vụ chuẩn xem `dashboard/README.md` và `scripts/smoke_test.py`.

LIVE: collector có mốc bắt đầu `2026-11-25T14:15:54.141Z`; mẫu cuối `2026-11-25T14:31:19.842Z` còn running; snapshot log gần nhất có received 35243, published 35242, parse_errors/publish_failed/reconnects đều 0. Các mẫu không loại trừ restart giữa các lần kiểm tra. Mẫu API `enwiki`: activity 17, trends 20, suspicious 20, event detail có dữ liệu; quét đệ quy bốn phản hồi không thấy sáu tên trường nhạy cảm nêu trong báo cáo. AppTest 4 trang không lỗi ở các lần lấy mẫu; không giám sát UI liên tục. Một bản ghi suspicious chọn theo `updated_at` mới nhất: `updated_at - event_time = 5,188s`, `generated_at - updated_at = 20,540s`; `updated_at` do Spark gán trước sink, không phải xác nhận Cassandra ghi xong; chưa hiệu chỉnh đồng hồ và không phải phép đo tới UI. Hai stack và volume riêng đã dọn, không commit payload LIVE.

### Cách kiểm tra lại REPLAY và LIVE trên bản clone sạch

Ví dụ PowerShell sau tạo project mới với tên ngẫu nhiên, dùng image đã build từ lượt smoke local; chỉ chạy `down --volumes` cho project đó. Chờ Spark xử lý fixture trước khi lấy mẫu; kết quả LIVE thay đổi theo thời điểm và nguồn. Không in hay lưu payload LIVE, tên bài viết hoặc định danh.

```powershell
$env:COMPOSE_PROJECT_NAME = 'wikipulse-check-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$env:COMPOSE_DISABLE_ENV_FILE = '1'
$env:PIPELINE_MODE = 'REPLAY'
$env:SPARK_ANALYTICS_SINK = 'cassandra'
$env:RUN_ID = 'manual-recheck'
$env:API_HOST_PORT = '0'
$env:DASHBOARD_HOST_PORT = '0'
$env:KAFKA_HOST_PORT = '0'
$env:KAFKA_ADVERTISED_EXTERNAL_PORT = '19092'
$env:KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
$env:TRIGGER_INTERVAL = '5 seconds'
$env:WIKI_ALLOWLIST = 'enwiki,viwiki'
$env:USER_HASH_SALT = 'local-demo-change-me'
docker compose up -d api spark dashboard
docker compose run --rm replay python -m replay.replay_producer --interval 0
```

Sau khi các service sẵn sàng và Spark đã xử lý dữ liệu, có thể chạy AppTest cho bốn trang bằng đoạn sau. `errors`/`exceptions` bằng 0 là điều kiện quan sát tại lượt chạy, không kiểm tra từng thao tác:

```powershell
$appTest = @'
import contextlib, io, json
from streamlit.testing.v1 import AppTest
out = {}
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    for page in ['Overview', 'Trending', 'Suspicious Edits', 'System Status']:
        app = AppTest.from_file('dashboard/app.py', default_timeout=40).run()
        app.radio(key='page').set_value(page).run()
        out[page] = {'exceptions': len(app.exception), 'errors': len(app.error),
                     'tables': len(app.dataframe), 'metrics': len(app.metric)}
print(json.dumps(out))
'@
$appTest | docker compose exec -T dashboard python -
docker compose stop api
$appTest | docker compose exec -T dashboard python -
docker compose start api
# Chờ API healthy, rồi chạy lại $appTest như trên.
docker compose down --volumes --remove-orphans
```

Để kiểm LIVE, dùng project ngẫu nhiên mới với cùng cấu hình, đổi `PIPELINE_MODE=LIVE`, bỏ lệnh replay và chạy `docker compose up -d api spark dashboard collector`. Ghi mốc `StartedAt` bằng `docker inspect` collector, lấy các snapshot trạng thái và bộ đếm tổng hợp trong log sau ít nhất 15 phút, rồi dọn project đó. Không commit log thô hoặc payload LIVE. Các kiểm tra chi tiết quét JSON và freshness ở lượt này đã dùng script tạm bị gitignore; công thức và phạm vi ở báo cáo, nhưng script và evidence chi tiết không có trong clone sạch. Để so sánh một cách đáng tin cậy cần lưu thêm evidence tổng hợp và quy trình đo có thể tái hiện.
