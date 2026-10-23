Trạng thái: REVIEW · Owner: Linh · Reviewer: Trọng, Nhân · Liên quan: W1-LINH-01; BL-THANH-01–05, BL-THANH-19–21

# W1-LINH-01 — Tiếp quản Spark/schema/Silver/activity

## Mục tiêu

Linh giải thích, kiểm thử và chạy lại được luồng Kafka → Bronze/invalid → Silver → activity Cassandra/Gold trên fixture REPLAY. Căn cứ [plans.md](../../plans.md), [checkpoint W1-LINH-01](../checkpoints.md), [contracts](../contracts.md) và [processing README](../../processing/README.md). Phần triển khai/kiểm chứng local đã hoàn tất; checkpoint REVIEW, chờ Trọng/Nhân review.

## Phạm vi / Không làm

- Tiếp quản `processing/spark/`, bổ sung test còn thiếu, sửa lỗi trong contract hiện hành nếu tái hiện được, cập nhật `processing/README.md` và plan này.
- Baseline đã có `RAW_EVENT_SCHEMA`, `SILVER_SCHEMA`, parsing/quarantine, ID ổn định, hash user, allowlist/canary, activity 1 phút; 5 query/checkpoint độc lập. Đã bổ sung 10 trường hợp kiểm thử vào baseline 8 test Spark + 8 test driver; evidence ở mục Kết quả.
- Dùng fixture CP0 và sample LIVE đã pseudonymize của Thành. Không sửa fixture/ingestion, Cassandra/API, Compose/Makefile hay docs của owner khác; phát hiện liên quan thì thêm backlog cho owner.
- Chạy regression dedup/watermark/Gold đã có. Nghiệp vụ trends/risk, mở rộng late data/recovery, Kafka DLQ và HDFS theo checkpoint tuần 2–3, không đưa vào khối lượng tuần 1.

## Các bước

Ngân sách 12 giờ: 8 giờ tiếp quản/phát triển, 2 giờ review/tích hợp, 2 giờ dự phòng; nằm trong mức 10–15 giờ của checkpoint. Các buổi tính từ lúc nhận việc, không suy diễn tuần kickoff theo ngày hiện tại.

| Bước | Giờ | Thực hiện | Đầu ra nghiệm thu |
|---|---:|---|---|
| 1. Tiếp quản và baseline | 1,5 | Đọc contract/config, lần theo 5 query; chuẩn bị Docker Linux containers, Python 3.11/Java 17/PySpark 3.5.6 theo image; build từ checkout hiện tại, chạy suite Spark và lightweight | Ghi commit, môi trường, số passed/failed/skipped; phân biệt lỗi môi trường với lỗi code |
| 2. Schema và validation | 2 | Đối chiếu kiểu/nullability, UTC, metadata Kafka, 4 error code; bổ sung ca chưa có như timestamp có offset, chuỗi rỗng/null và fallback epoch; lỗi invalid không chặn event hợp lệ | Assertions theo contract cho Silver và quarantine; không bổ sung test chỉ lặp implementation |
| 3. Event ID và Silver | 2 | Kiểm `meta.id` ưu tiên; ID fallback ổn định khi đổi ingest/Kafka metadata và khác khi đổi sự kiện; thêm ca ID rỗng/whitespace còn thiếu; kiểm hash/privacy, allowlist, nullable fields; chạy regression dedup/restart | Không raw user/comment trong Silver; giữ schema đọc Parquet; duplicate trong horizon không thêm dòng |
| 4. Activity và sample | 2,5 | Kiểm cửa sổ UTC 1 phút, tách wiki, phân loại edit/new và anonymous/bot edits; đối chiếu fixture expected độc lập. Đưa sample LIVE qua parser/normalizer để kiểm thiếu page_id/anon, categorize/log/canary; phân loại vấn đề theo backlog | Counts CP0 khớp expected; sample xử lý không làm crash; ghi rõ giới hạn LIVE, không hợp thức hóa sai số đã biết bằng test kỳ vọng sai |
| 5. Tích hợp và review | 2 | Chạy smoke cô lập; xem output Parquet và activity API; cập nhật README/evidence; Trọng review pipeline, Nhân review DataFrame bàn giao sink; trao đổi đầu vào với Thành | PR có test/log/sample output an toàn; chuyển checkpoint REVIEW khi sẵn sàng, DONE khi đạt tiêu chí và review xong |
| 6. Dự phòng | 2 | Build image, lỗi Windows/encoding, sửa regression trong phạm vi | Nếu vượt 15 giờ, ghi blocker và tách phần mở rộng theo backlog |

- [x] Hoàn thành baseline và ghi evidence mới của Linh.
- [x] Hoàn thành test/sửa lỗi schema, validation, ID, Silver, activity còn thiếu.
- [x] Kiểm sample LIVE và rà các quyết định phụ thuộc.
- [x] Hoàn thành smoke nghiệm thu và docs; cập nhật checkpoint bằng link tới plan này.
- [ ] Trọng + Nhân review phần bàn giao; chưa có PR hoặc xác nhận review.

## Quyết định

- Giữ kiến trúc 5 query và ranh giới Silver Parquet; không ghép dedup với aggregation trong một query Update. Activity gửi tổng tuyệt đối, không delta; giữ contract v0.1.
- [BL-THANH-01–05](../backlog.md#cần-nhóm-quyết-định): cần trao đổi allowlist, DLQ, collector version, delivery/late data và ý nghĩa metrics với các owner ghi trong backlog. Tuần 1 tiếp tục REPLAY theo contract hiện hành; không phải chờ collector LIVE.
- [BL-THANH-19–21](../backlog.md#linh): đã xác nhận bằng sample và event tổng hợp các vấn đề temporary account, canary thiếu wiki và missing user hash. BL-THANH-19/20 đã nhận lịch tuần 2; BL-THANH-21 chưa có lịch. Tuần 1 ghi kết quả tái hiện; chỉ sửa hành vi sau khi chốt phạm vi và review contract nếu ảnh hưởng consumer.
- Phát hiện mâu thuẫn contract thì dừng phần code liên quan để producer/consumer thống nhất; vẫn tiếp tục kiểm thử các phần độc lập. Không tự đóng backlog hay checkpoint của người khác.
- Branch triển khai: `linh/w1-linh-01-spark-takeover`; không commit/push khi người dùng chưa yêu cầu.

Rà soát phụ thuộc tuần 2 (đề xuất kỹ thuật, không phải xác nhận của reviewer):

| Item | Kết luận cho W1 / đề xuất bàn giao |
|---|---|
| BL-THANH-01 | Test giữ wiki ngoài allowlist ở Bronze, bỏ khỏi Silver đúng v0.1; đề xuất tiếp tục lọc ở Silver. |
| BL-THANH-02 | Quarantine Parquet đáp ứng W1; Trọng/Thành/Linh cần chốt Kafka DLQ trước triển khai W2. |
| BL-THANH-03 | Spark không dùng `collector_version` để tạo ID/count; đề xuất nhận prefix replay/live của producer, chờ duyệt quy ước W2. |
| BL-THANH-04 | Test dedup qua batch/restart pass trong horizon; không suy rộng thành exactly-once hoặc bảo đảm replay sau 10 phút. |
| BL-THANH-05 | Sample xác nhận categorize/log tăng event_count nhưng không tăng edit_count; giữ semantics hiện hành, Nhân/Mạnh cùng review cách hiển thị trước LIVE. |

## Nhật ký

- 2026-10-20 — Đọc repo tại commit `f42295969e6a766c84d40fa95ea80753d5d42968`; đối chiếu kế hoạch, checkpoint, backlog, contracts, code/test Spark và sample; lập kế hoạch. Chưa có PR/commit cho thay đổi này.
- 2026-10-20 — Bắt đầu bước 1: dùng `.venv` người dùng đã tạo tại `D:\bigdata\.venv`, kiểm tra Docker Desktop, cài dependencies và chạy baseline/unit/Spark/smoke; sẽ ghi kết quả thực tế bên dưới. Chưa commit/push.
- 2026-10-20 — Hoàn tất bước 1: dependencies/build/config/lint pass; lightweight 121 passed, Spark 16 passed; smoke `smoke-20261020103303-f627c10ad3154ea591650d2ba44ec13c` passed và đã cleanup. Tạo branch `linh/w1-linh-01-spark-takeover`; chưa sửa mã nghiệp vụ, chưa commit/push. Các bước bổ sung test và kiểm sample LIVE qua Spark vẫn còn trong kế hoạch.
- 2026-10-20 — Bắt đầu phần còn lại: thêm test biên UTC/validation/ID/privacy/activity, chạy sample LIVE qua Spark với báo cáo tổng hợp không chứa danh tính, đối chiếu backlog và hoàn thiện README/evidence. Giữ contract v0.1; các phát hiện LIVE được ghi nhận, không đổi định nghĩa metrics khi chưa có review producer/consumer.
- 2026-10-20 — Hoàn tất phần local: thêm 10 trường hợp test, Spark/driver 26 passed, lightweight 121 passed, Ruff pass; sample LIVE và ba finding đã tái hiện. Smoke nghiệm thu mới `smoke-20261020104512-69707a30e9984515ae55ece81c56ffd7` passed và đã cleanup. Cập nhật README/backlog/checkpoint REVIEW, chuẩn bị evidence để reviewer chạy lại; chưa commit/push và chưa có review từ thành viên.

## Kết quả

Đã hoàn tất test bổ sung và chạy sample LIVE qua Spark trên working tree dựa trên commit `f42295969e6a766c84d40fa95ea80753d5d42968`. Thay đổi là tests/docs; không cần sửa mã nghiệp vụ trong phạm vi contract W1 sau các kiểm tra này. Chưa commit, chưa có review của Trọng/Nhân. `artifacts/linh-w1-handoff/source-manifest.json` ghi SHA-256 test source, transformations, fixture LIVE và contracts để nhận diện đúng mã đã kiểm.

Môi trường ngày 20/10/2026: Windows, Python 3.11.5 trong `D:\bigdata\.venv`, Docker Engine 29.1.3, Compose v5.0.0-desktop.1, Linux/x86_64, 16 CPU, khoảng 11,5 GiB RAM cho Docker. Dependencies đã cài từ `.[dev]` và `dashboard/requirements.txt`; tạo `.env` từ `.env.example`; build thành công image api/spark/dashboard/replay và pull các image hạ tầng. Spark dùng PySpark 3.5.6/Python 3.11/Java 17 trong container.

| Kiểm tra | Kết quả mới | Evidence local |
|---|---|---|
| Dependencies | Cài thành công; `pip check`: No broken requirements found | `artifacts/linh-w1-baseline/pip-install.log`, `pip-check.log`, `dependencies.txt` |
| Unit/API/dashboard/ingestion/replay/driver | 121 passed, 23 deselected, 2 deprecation warnings từ thư viện; 5,35 giây | `artifacts/linh-w1-handoff/unit-tests.log`, `unit-tests.xml` |
| Spark + driver trong container | 26 passed, không skip/xfail; 29,58 giây | `artifacts/linh-w1-handoff/spark-tests.log` |
| Sample LIVE qua Spark | Assertions pass; findings còn OPEN, xem mục Sample LIVE | `artifacts/linh-w1-handoff/live-sample-report.json` |
| Ruff | All checks passed | `artifacts/linh-w1-handoff/lint.log` |
| Compose | Configuration valid | `artifacts/linh-w1-baseline/compose-config.log` |
| E2E smoke nghiệm thu | passed; Bronze 11 / invalid 2 / Silver 7 / Gold target 2; API và dashboard đúng fixture | `artifacts/smoke-20261020104512-69707a30e9984515ae55ece81c56ffd7/report.json`, `artifacts/linh-w1-handoff/smoke.log` |

Các nhóm test có phần driver trùng nhau, không cộng hai số passed thành tổng test độc lập. `artifacts/linh-w1-baseline/environment.json` ghi interpreter, commit, branch và phiên bản thư viện. Test integration được loại khỏi lightweight suite theo lệnh chuẩn; E2E được kiểm riêng bằng smoke.

Smoke nghiệm thu `smoke-20261020104512-69707a30e9984515ae55ece81c56ffd7` có `commands.log`, `services.log` và `report.json` trong thư mục tương ứng dưới `artifacts/`. Script đã kết thúc với exit code 0 và dọn container/volume/network của project test; URL động trong report là địa chỉ lúc kiểm thử, không còn phục vụ sau cleanup. Evidence là file local được gitignore; gói `artifacts/linh-w1-evidence-20261020.zip` chứa log nghiệm thu, report, manifest nguồn và thông tin môi trường để đính kèm review.

Lệnh tái hiện từ thư mục repo, dùng `.venv` thực tế ở thư mục cha; PowerShell đặt UTF-8 theo [BL-THANH-06/11](../backlog.md#trọng). Lần chạy đã lưu stdout/stderr vào các log trong bảng trên:

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]" -r dashboard/requirements.txt
docker compose build api spark dashboard replay
docker compose pull kafka cassandra init-kafka-volume
docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q --capture=tee-sys
$env:PYTHONUTF8 = "1"
..\.venv\Scripts\python.exe -m pytest -q -m "not integration and not spark" --junitxml=artifacts/linh-w1-handoff/unit-tests.xml
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m pip check
docker compose config --quiet
..\.venv\Scripts\python.exe scripts\smoke_test.py --no-build
```

### Sample LIVE

Fixture `recentchange_live_sample.jsonl` được đọc từ đĩa bằng Spark thật, không kết nối SSE. Kết quả: Bronze 11 / Silver 9 / invalid 1 (canary); wiki ngoài allowlist vẫn có ở Bronze. Không business event hợp lệ nào bị quarantine; page_id nullable, timestamp mili-giây, hash user và nullable revision/length đều được assert.

Counts đếm độc lập từ fixture, tuple `(event, edit, new, bot_edit)`:

| Wiki | Window UTC ngày 15/10/2026 | Counts |
|---|---|---|
| enwiki | 10:13 | (4, 3, 0, 1) |
| enwiki | 10:14 | (2, 2, 0, 0) |
| enwiki | 10:15 | (1, 0, 0, 0) |
| enwiki | 10:16 | (1, 0, 1, 0) |
| viwiki | 10:14 | (1, 1, 0, 0) |

Findings được báo cáo riêng, không biến hành vi sai thành expected assertion:

- BL-THANH-19: 1 edit của temporary account, 0 được nhận diện anonymous.
- BL-THANH-20: canary vào invalid với `MISSING_WIKI`, không vào Silver/activity.
- BL-THANH-21: hai event tổng hợp thiếu user/user=null có hai hash non-null nhưng chỉ một hash phân biệt. Fixture LIVE không có ca missing-user.

Đã nhận các finding thành OPEN; BL-THANH-19/20 thuộc W2-LINH-01, BL-THANH-21 chưa có lịch. Hướng dẫn chạy và giới hạn nằm trong [processing README](../../processing/README.md#week-one-verification). Log `LIVE_SAMPLE_REPORT=` chỉ gồm counts/flags/error codes, không raw payload, tên tài khoản, title hay hash.

### Bàn giao review

- Trọng: kiểm ranh giới 5 query, coverage UTC/validation/ID/Parquet và evidence CP0.
- Nhân: kiểm schema activity 9 trường/tổng tuyệt đối, nullable Silver và các ảnh hưởng consumer trong BL-THANH-19/21; BL-THANH-05 cần thêm Mạnh.
- Thành: đối chiếu fixture/envelope và các đề xuất BL-THANH-01–04 trước W2; chưa có xác nhận trao đổi với các thành viên.
- Tên commit đề xuất: `test(spark): verify week-one contracts and live sample`; bản thay đổi và evidence đã chuẩn bị local, chưa tạo PR.

Điều kiện đóng việc:

- Tests bắt buộc pass, không bỏ qua test Spark do thiếu PySpark/JVM; sửa code phải build lại image trước khi kiểm tra.
- Smoke run mới có Bronze 11 / invalid 2 / Silver 7; Gold có 2 dòng tại cửa sổ `2026-01-01T00:00:00Z`. Counts theo [expected_activity.json](../../tests/fixtures/expected_activity.json): enwiki `(event, edit, new, anonymous_edit, bot_edit) = (5, 5, 0, 1, 1)`; viwiki `(1, 0, 1, 0, 0)`.
- Smoke gửi fixture theo phase: đợi provisional counts rồi mới gửi event tiến watermark; không đợi wall clock tự finalize và không replay nhiều lần vào checkpoint dev để đối chiếu totals.
- Kết quả ghi lệnh, commit, môi trường, output thực tế; trỏ tới `artifacts/smoke-*/report.json`, `commands.log`, `services.log` của lần chạy. Sample output bàn giao chỉ gồm schema/counts/field an toàn, không raw username/IP.
- Trọng và Nhân review; README mô tả đúng hành vi/giới hạn; checkpoint chỉ link plan khi đổi trạng thái. Việc này đóng góp CP1, không tự đánh DONE CP1 chung.
