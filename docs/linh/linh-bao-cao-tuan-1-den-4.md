Trạng thái: DONE · Owner: Linh · Reviewer dự kiến: Trọng, Nhân · Liên quan: W1-LINH-01, W2-LINH-01, W3-LINH-01, W4-LINH-01

# Báo cáo tổng hợp công việc của Linh — Tuần 1 đến tuần 4

**Dự án:** WikiPulse — Phân tích xu hướng Wikipedia và phát hiện chỉnh sửa đáng chú ý theo thời gian thực.

**Vai trò:** Spark/analytics, phụ trách module `processing/`.

**Ngày tổng hợp:** 25/11/2026.

**Nguồn đối chiếu:** checkout `linh/w4-linh-01-correctness`, commit `d818855`, các plan tuần, checkpoint và evidence lưu trên máy.

## 1. Mục tiêu và phạm vi báo cáo

Báo cáo tổng hợp quá trình Linh tiếp quản pipeline Spark, triển khai analytics, kiểm chứng lưu trữ HDFS và hoàn thiện kiểm thử/tài liệu bàn giao qua bốn tuần. Các mốc triển khai được ghi nhận từ 20/10 đến 16/11/2026; ngày tổng hợp không phải ngày chạy lại các bộ kiểm thử.

Khung CP0, hạ tầng chung và luồng REPLAY ban đầu do Trọng xây dựng. Linh tiếp quản phần xử lý, bổ sung kiểm thử và mở rộng nghiệp vụ theo phân công trong [kế hoạch tổng](../../plans.md). Collector/replay thuộc Thành, Cassandra/API thuộc Nhân, dashboard thuộc Mạnh; báo cáo chỉ ghi phần Linh thực hiện hoặc trực tiếp kiểm chứng khi tích hợp.

Trạng thái dưới đây phản ánh [checkpoints](../checkpoints.md) tại checkout đã đọc. Phiên tổng hợp này không kiểm tra lại trạng thái push, PR hoặc merge mới nhất trên GitHub. Các plan tuần là nguồn chi tiết; báo cáo này là bản tổng hợp lộ trình cá nhân, không thay thế contract hay nhật ký nghiệm thu.

## 2. Tổng quan kết quả bốn tuần

| Tuần | Mục tiêu | Công việc và sản phẩm chính của Linh | Trạng thái ghi nhận |
|---|---|---|---|
| 1 | Tiếp quản schema, Silver và activity | Bổ sung 10 trường hợp kiểm thử; chạy lại CP0; kiểm tra sample LIVE; tái hiện ba vấn đề dữ liệu đầu vào | `REVIEW`: phần local hoàn tất, chờ review |
| 2 | Windows, features, risk và trends | Silver v0.2; cấu hình scoring; ba đầu ra analytics; bốn query mới; golden tests và callback bàn giao sink | `DONE` trong phạm vi producer |
| 3 | Bronze/Silver/Gold trên HDFS | Lab riêng; runner nghiệm thu bảy phase với Kafka/HDFS/Cassandra thật; kiểm tra partitions, late data, restart và retry | `DONE` trong phạm vi Spark/HDFS của Linh |
| 4 | Correctness và bàn giao | Regression bổ sung; củng cố test metadata bằng giả lập lỗi; tài liệu công thức/giới hạn; chạy lại nghiệm thu HDFS | `REVIEW`: phần độc lập sẵn sàng, chờ review/tích hợp |

Kết quả xuyên suốt là phần producer Spark có thể xử lý REPLAY qua Bronze/invalid, Silver, activity và analytics; ghi dữ liệu/state trên HDFS; khôi phục checkpoint; và đối chiếu đầu ra với kỳ vọng độc lập. Phần serving analytics qua Cassandra/API và luồng LIVE toàn hệ thống vẫn cần phối hợp với các owner liên quan theo hồ sơ bàn giao hiện có.

## 3. Tuần 1 — Tiếp quản Spark, schema, Silver và activity

**Mốc thực hiện:** 20/10/2026. **Nguồn:** [W1-LINH-01](../plans/W1-LINH-01.md).

### 3.1. Chuẩn bị môi trường và tiếp quản kiến trúc

- Sử dụng venv tại `D:\bigdata\.venv`, chuẩn bị dependencies và Docker Linux containers.
- Build các image cần cho kiểm thử; chạy Spark với Python 3.11, Java 17 và PySpark 3.5.6 trong container.
- Đọc contract, config và lần theo năm query/checkpoint sẵn có: Bronze raw, Bronze invalid, Silver events, activity Cassandra và activity Gold.
- Nắm ranh giới Silver Parquet: khử trùng lặp trước khi các query độc lập đọc Silver để tổng hợp. Activity gửi tổng tuyệt đối sang sink; Gold nhận cửa sổ đã chốt theo watermark.

### 3.2. Bổ sung kiểm thử hợp đồng dữ liệu

Linh bổ sung 10 trường hợp kiểm thử trong [test_transformations.py](../../processing/spark/tests/test_transformations.py), tập trung vào:

- Chuyển thời gian về UTC, timestamp có offset, độ chính xác mili-giây, ưu tiên nguồn thời gian và fallback epoch.
- Phân loại dữ liệu hợp lệ/không hợp lệ; trường nullable; sự kiện chỉ có title hoặc page ID; partitions ngày/giờ.
- Ưu tiên `meta.id`, xử lý ID rỗng và tính ổn định của ID fallback khi metadata ingest/Kafka thay đổi.
- Hash người dùng có salt, loại trường định danh/comment thô khỏi Silver và kiểm tra đọc/ghi Parquet.
- Cửa sổ activity một phút, tách wiki, phân loại edit/new và các bộ đếm anonymous/bot; schema phẳng phục vụ sink.
- Chạy lại các kiểm tra dedup, restart và Gold finalized đã có trong baseline.

### 3.3. Kiểm tra sample LIVE và chuyển phát hiện sang tuần 2

Sample đã pseudonymize của Thành được đọc từ file và xử lý bằng Spark thật. Đây là kiểm tra dữ liệu mẫu, không phải chạy collector SSE LIVE.

| Phát hiện | Kết quả quan sát ở tuần 1 | Hướng xử lý |
|---|---|---|
| `BL-THANH-19` — temporary account | Một edit thuộc temporary account chưa được nhận diện anonymous | Chuyển sang normalization v0.2 |
| `BL-THANH-20` — canary thiếu business fields | Canary bị đưa vào invalid với `MISSING_WIKI` | Nhận diện canary trước validation business |
| `BL-THANH-21` — người dùng thiếu/null | Hai sự kiện tổng hợp nhận hash không-null dù không có người dùng | Chuyển hash của user thiếu/null/blank thành null |

Sample tuần 1 có **11 Bronze, 9 Silver và 1 invalid**; dòng invalid là canary. Wiki ngoài allowlist vẫn được giữ trong Bronze. Các phát hiện được ghi vào backlog và plan, không sửa âm thầm định nghĩa dữ liệu khi đang tiếp quản contract v0.1.

### 3.4. Kết quả kiểm chứng và bàn giao

- Baseline Spark/driver: **16 passed**; sau bổ sung: **26 passed**.
- Lightweight toàn repo: **121 passed**; Ruff pass.
- Smoke CP0 mới đạt `passed`: **Bronze 11, invalid 2, Silver 7, Gold activity 2**; activity API/Overview được kiểm tra trong luồng tích hợp.
- Cập nhật processing README, plan, backlog và checkpoint `REVIEW`; chuẩn bị log, báo cáo mẫu và gói evidence.

Commit tuần 1 chủ yếu bổ sung kiểm thử và tài liệu tiếp quản; phần pipeline CP0 nền đã có trước đó.

## 4. Tuần 2 — Triển khai analytics và scoring

**Mốc thực hiện:** 30/10/2026. **Nguồn:** [W2-LINH-01](../plans/W2-LINH-01.md).

### 4.1. Sửa normalization và hoàn thiện Silver v0.2

- Thêm `is_revert`; nhận diện các mẫu comment hoàn tác tiếng Anh theo contract trước khi loại comment khỏi Silver.
- Nhận diện temporary account là anonymous, kể cả khi cờ `anon` của đầu vào là false.
- Nhận diện canary trước validation business; giữ trong Bronze, loại khỏi Silver và không đưa vào invalid chỉ vì thiếu wiki/title.
- Để `user_hash` là null khi user thiếu/null/blank, tránh đếm một người dùng giả trong số editor duy nhất.
- Bổ sung regression cho ba phát hiện từ tuần 1. Sample LIVE sau sửa đạt **11 Bronze, 9 Silver, 0 invalid**; temporary edit được nhận diện đúng; các trường hợp thiếu user không còn hash không-null.

### 4.2. Triển khai features, cửa sổ và ba đầu ra analytics

| Đầu ra | Xử lý chính | Sản phẩm bàn giao |
|---|---|---|
| Trends | Cửa sổ 5 phút trượt 1 phút; chỉ edit, gồm bot; tổng edit, editor duy nhất ước lượng và tổng độ lớn thay đổi byte; metadata ổn định theo khóa trang | DataFrame trends tạm tính, changelog Parquet và Gold trends finalized |
| Suspicious edits | Tính các lý do `LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`; chỉ xuất edit có điểm dương | DataFrame/Parquet suspicious, bucket theo phút |
| Event detail | Xuất mọi sự kiện Silver cùng điểm/lý do risk và metadata phục vụ tra cứu | DataFrame/Parquet event detail, loại user/hash/comment thô khỏi đầu ra phục vụ |

Activity một phút và watermark 10 phút tiếp tục được giữ. Các công thức, schema và điều kiện biên theo [contract v0.2](../contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02).

### 4.3. Cấu hình, queries và giao diện sink

- Triển khai loader cho `config/scoring.yaml`, kiểm tra khóa cấu hình, kiểu số, giá trị hữu hạn, tổng trọng số, caps, threshold và giới hạn điểm trước khi khởi chạy queries.
- Thêm dependency PyYAML 6.0.2 vào Spark image và hướng dẫn môi trường.
- Giữ năm query CP0, bổ sung bốn query analytics, nâng tổng lên **chín query/checkpoint độc lập**.
- Thêm đường dẫn dữ liệu/state riêng theo `RUN_ID`; yêu cầu namespace mới khi thay đổi schema, scoring hoặc sink mode.
- Bổ sung adapter/callback `AnalyticsBatchWriter` để bàn giao các hàng UTC theo schema cho store; xử lý lỗi sink bằng cách làm batch/query thất bại để có thể retry.
- Hỗ trợ `SPARK_ANALYTICS_SINK=parquet` cho producer handoff. Mode Cassandra kiểm tra đủ `upsert_trends`, `upsert_suspicious_edits`, `upsert_events` và fail rõ khi store chưa triển khai.
- Changelog trends lưu tổng tuyệt đối theo `batch_id`; đọc giá trị mới nhất cho từng khóa thay vì cộng các snapshot. Retry ghi lại cùng batch directory.

### 4.4. Kết quả kiểm chứng

- Golden fixtures và expected results được lưu độc lập với biểu thức tính toán; kiểm thử theo hướng test-first đã phát hiện phần implementation còn thiếu trước khi hoàn thiện.
- Bộ Spark/driver/config/streaming: **66 passed**, không skip/xfail trong lượt nghiệm thu này.
- Lightweight: **127 passed**; Ruff pass; smoke CP0 với Kafka thật pass.
- Kiểm tra analytics trên cùng run: **7 events, 3 suspicious edits**; điểm risk của ba fixture mục tiêu lần lượt **10, 30, 20**.
- Kiểm tra Gold trends: hai trang mục tiêu có điểm **0.12475** và **0.022625**, đúng kỳ vọng độc lập; duplicate không làm tăng trends.
- Kiểm tra cửa sổ chồng lấp, caps, null/bot/temporary account, metadata ổn định, late data, restart, finalized và callback retry.

Phần producer tuần 2 được đánh dấu `DONE`. Việc triển khai store/CQL/endpoints analytics thuộc Nhân và được theo dõi bằng `BL-LINH-02`; output Parquet là đầu ra bàn giao có thể kiểm chứng trong thời gian chờ tích hợp.

## 5. Tuần 3 — HDFS, persistence và phục hồi

**Mốc chuẩn bị:** 04/11/2026. **Mốc nghiệm thu:** 08/11/2026. **Nguồn:** [W3-LINH-01](../plans/W3-LINH-01.md).

### 5.1. Chuẩn bị và bảo toàn môi trường

- Tạo lab HDFS riêng trong `processing/spark/dev/`, gồm NameNode/DataNode, replication 1 và named volumes độc lập.
- Viết probe ghi/đọc dữ liệu synthetic, partitions và namespace checkpoint; kiểm tra dữ liệu còn đọc được sau restart.
- Phân biệt cấu hình HDFS của probe với cấu hình filesystem local cho unit tests, xử lý trường hợp fixture local bị đọc nhầm qua HDFS.
- Giữ venv, images, volumes và evidence đã có; dừng lab khi chưa cần dùng.
- Khi profile full do Trọng bàn giao có trên nền `312c086`, đưa vào nhánh làm việc và dùng profile chung cho nghiệm thu. Lab chuẩn bị dùng Hadoop 3.4.1; nghiệm thu full dùng Hadoop 3.4.3.

### 5.2. Xây runner nghiệm thu pipeline thật

Linh bổ sung [run_hdfs.py](../../processing/spark/acceptance/run_hdfs.py), [phase_job.py](../../processing/spark/acceptance/phase_job.py), fixture theo phase và expected JSON. Runner dùng production query starter cùng Kafka, HDFS và Cassandra activity thật, tạo project/RUN_ID riêng và tự dọn tài nguyên của lượt thử.

Production query starter tuần 2 đã hỗ trợ URI HDFS. Phần bổ sung tuần 3 tập trung vào môi trường, fixture, kiểm chứng và hướng dẫn chạy; hạ tầng full dùng chung do Trọng sở hữu.

| Phase | Tình huống được kiểm chứng |
|---|---|
| `initial` | Fixture qua nửa đêm UTC; JSON lỗi/missing page; canary; Gold chưa chốt |
| `late` | Duplicate cùng ID, kể cả timestamp thay đổi trong horizon; late event hợp lệ cập nhật cửa sổ còn mở |
| `retry_failure` | Cố ý gây lỗi sau khi Cassandra đã upsert activity thành công |
| `recovered` | Spark mới dùng checkpoint cũ, chạy lại batch lỗi; activity vẫn 3, không thành 6 |
| `finalized` | Tạo lại HDFS containers với volumes cũ; clock event tiến watermark và chốt Gold |
| `after_restart` | Tạo lại HDFS lần nữa; gửi duplicate cũ, sự kiện quá muộn và sự kiện mới |
| `idle_restart` | Restart không có input mới; số dòng và kết quả đã chốt giữ nguyên |

### 5.3. Các bất biến đã kiểm tra

- Bronze/invalid/Silver partition theo ngày/giờ UTC; Gold partition theo ngày/giờ của cửa sổ và wiki, có kiểm tra đường dẫn vật lý.
- Bronze không lặp tọa độ Kafka; Silver, events, suspicious và Gold không lặp khóa logic trong fixture nghiệm thu.
- Chín query giữ nguyên persistent query ID khi phục hồi checkpoint; execution run ID thay đổi qua các JVM mới.
- Data và checkpoint đều ở HDFS; trạng thái còn nguyên qua hai lần tạo lại NameNode/DataNode.
- Gold chỉ xuất hiện sau khi event time tiến watermark; dữ liệu quá muộn và idle restart không mở lại cửa sổ đã chốt.
- Privacy fields và phân loại invalid/canary khớp kỳ vọng.

### 5.4. Kết quả và các vấn đề đã xử lý khi nghiệm thu

- Acceptance đạt **7/7 phase**; full smoke chung cũng `passed` cho activity/API/UI và analytics Parquet.
- Kết quả cuối: **Bronze 13, invalid 2, Silver 6, events 6, suspicious 2, Gold activity 2, Gold trends 10**.
- Cửa sổ/trang mục tiêu có **3 edits, 3 editors, tổng độ lớn byte 650, trend score 0.08375**; kết quả giữ nguyên sau retry/restart/too-late.
- Spark regression: **66 passed**; Windows lightweight: **138 passed**; bootstrap POSIX trong Linux: **5 passed**; hai cấu hình Compose core/full được kiểm tra riêng.
- Sửa runner để đợi daemon rồi chạy one-shot init riêng, vì Compose v5 `--wait` không coi container init đã exit 0 là service đang chạy.
- Dùng schema rõ ràng khi đọc Gold còn rỗng trước watermark, tránh lỗi infer schema từ output chỉ có metadata.
- Cập nhật processing README theo các biến môi trường đã được Compose forward và hướng dẫn nghiệm thu HDFS.

## 6. Tuần 4 — Correctness, golden results và tài liệu bàn giao

**Mốc thực hiện:** 16/11/2026. **Nguồn:** [W4-LINH-01](../plans/W4-LINH-01.md).

### 6.1. Rà soát và bổ sung regression

- Tạo nhánh tuần 4 từ commit tuần 3, kiểm tra lại venv, image runtime và cấu hình Compose.
- Đối chiếu implementation analytics/scoring với contract, golden W2/W3 và các giới hạn xử lý.
- Thêm [test_week_four.py](../../processing/spark/tests/test_week_four.py) để kiểm tra kết hợp các risk rule, bot/non-edit, ranh giới cửa sổ và chọn metadata khi nhiều sự kiện cùng timestamp.
- Risk mặc định trong các ca tổng hợp đạt **60/50/0/0** tương ứng edit thường, edit bot, new và log. Golden trend mới là **0.0335** và **0.023**.
- Chạy regression **68 passed** và lightweight **138 passed**, Ruff pass; chạy lại acceptance HDFS đạt **7/7 phase** với chín checkpoint giữ nguyên danh tính.

### 6.2. Cải thiện sau review

Review phát hiện fixture metadata ban đầu có thứ tự `event_id` và title cùng chiều. Nếu giả lập code ưu tiên title trước event_id, test vẫn pass dù sai contract. Linh đã:

1. Đổi dữ liệu thành `a/Zulu/namespace=2` và `b/Alpha/namespace=1` cùng timestamp, đặt thứ tự title/namespace ngược event_id.
2. Assert kết quả phải chọn `Alpha/1` ở cả hai thứ tự nhận, đồng thời kiểm tra metadata của cửa sổ tiếp theo.
3. Chạy lại hai test tuần 4: **2 passed**. Giả lập lại lỗi chỉ trong bộ nhớ: test thất bại đúng tại `Zulu/2 != Alpha/1`; script kiểm chứng trả `MUTATION_CHECK=passed`.
4. Cập nhật mục tiêu/phạm vi plan để phản ánh công việc thực tế và sửa đường dẫn test trong processing README.
5. Cập nhật ZIP evidence; kiểm tra CRC, source snapshot và các log review khớp file hiện tại.

Dòng `1 failed` trong log giả lập lỗi là kết quả mong đợi để chứng minh khả năng bắt regression. Sau chỉnh sửa fixture chỉ chạy lại test liên quan; kết quả 68 test toàn bộ và HDFS được ghi rõ là lượt trước chỉnh sửa này. Logic production không thay đổi trong tuần 4.

### 6.3. Hoàn thiện tài liệu

Processing README được bổ sung công thức trend/risk, ví dụ tính tay, độ chính xác ước lượng editor, quy tắc metadata, điều kiện finalize và giới hạn phục hồi. Phần bàn giao làm rõ: mặc định ba risk rule cho tối đa 60 điểm, ngưỡng 100 là trần cấu hình; risk là tín hiệu ưu tiên xem xét, không kết luận phá hoại.

Tuần 4 giữ `REVIEW`, sẵn sàng bàn giao phần độc lập. Review của Trọng/Nhân và tích hợp theo CP3 vẫn là các bước còn chờ trong plan.

## 7. Danh mục sản phẩm bàn giao

| Nhóm | File/thư mục chính | Đóng góp của Linh |
|---|---|---|
| Normalization và Silver | [transformations.py](../../processing/spark/wikipulse/transformations.py) | Tiếp quản, kiểm thử contract; sửa ba vấn đề LIVE và thêm Silver v0.2 |
| Analytics và scoring | [analytics.py](../../processing/spark/wikipulse/analytics.py), [scoring.py](../../processing/spark/wikipulse/scoring.py) | Biểu thức trends/risk/detail và loader cấu hình |
| Query/sink integration | [analytics_queries.py](../../processing/spark/wikipulse/analytics_queries.py), [sinks.py](../../processing/spark/wikipulse/sinks.py), [paths.py](../../processing/spark/wikipulse/paths.py) | Bốn query analytics, adapters/changelog, paths và checkpoints |
| Entrypoint/runtime | [streaming_job.py](../../processing/spark/jobs/streaming_job.py), [Dockerfile](../../processing/spark/Dockerfile), [requirements-scoring.txt](../../processing/spark/requirements-scoring.txt) | Nối analytics vào pipeline và cài dependency scoring |
| Regression/golden | [tests](../../processing/spark/tests), [fixtures](../../processing/spark/tests/fixtures) | Test tuần 1/2/4, callback/config, fixture W2 và fixture theo phase W3 |
| Môi trường HDFS | [compose.hdfs.yaml](../../processing/spark/dev/compose.hdfs.yaml), [hdfs_probe.py](../../processing/spark/dev/hdfs_probe.py) | Lab riêng và probe persistence |
| Nghiệm thu HDFS | [acceptance](../../processing/spark/acceptance) | Runner bảy phase và assertions trên các dịch vụ thật |
| Tài liệu/điều phối | [processing README](../../processing/README.md), bốn plan tuần, [contracts](../contracts.md), [backlog](../backlog.md), [checkpoints](../checkpoints.md) | Hướng dẫn chạy, giới hạn, giao diện producer, findings và evidence |

Ở mode analytics Parquet đã nghiệm thu, chín query gồm `bronze_raw`, `bronze_invalid`, `silver_events`, `activity_cassandra`, `activity_gold`, `trends_provisional_parquet`, `suspicious_parquet`, `events_parquet`, `trends_gold`. Sơ đồ output và các lệnh tái hiện được duy trì tại [processing README](../../processing/README.md).

## 8. Tổng hợp evidence và lịch sử commit

### 8.1. Bảng kiểm thử

| Mốc | Spark/driver/config | Lightweight | Nghiệm thu tích hợp |
|---|---|---|---|
| W1 | 26 passed sau bổ sung | 121 passed | Smoke CP0 passed |
| W2 | 66 passed | 127 passed | Smoke CP0 và inspection analytics passed |
| W3 | 66 passed | 138 passed | HDFS 7/7; full smoke passed; thêm 5 test POSIX và 2 kiểm tra config Compose |
| W4 trước cải thiện review | 68 passed | 138 passed | Chạy lại HDFS 7/7 |
| W4 sau cải thiện review | 2 test liên quan passed | Không chạy lại | Giả lập lỗi bị test bắt đúng; xác minh ZIP |

Đây là các lượt chạy ở những thời điểm khác nhau, có test lặp và có phần driver xuất hiện trong nhiều bộ. Không cộng các con số thành tổng test độc lập hoặc coi toàn bộ test trong repo là do Linh viết.

| Tuần | Gói evidence local | Report nghiệm thu tiêu biểu |
|---|---|---|
| W1 | `artifacts/linh-w1-evidence-20261020.zip` | `artifacts/smoke-20261020104512-69707a30e9984515ae55ece81c56ffd7/report.json` |
| W2 | `artifacts/linh-w2-evidence-20261030.zip` | `artifacts/smoke-20261030084350-d07a74cacd65480d84457ffa3f1e4255/report.json` |
| W3 | `artifacts/linh-w3-evidence-20261108.zip` | `artifacts/w3-20261108084619-0608715eade6/report.json` |
| W4 | `artifacts/linh-w4-evidence-20261116.zip` | `artifacts/w3-20261116142755-9571ad62d2f7/report.json` |

Đường dẫn evidence tính từ root repo. `artifacts/` được gitignore; reviewer clone repo cần nhận các gói ZIP riêng hoặc chạy lại theo README. Run W4 giữ tiền tố `w3-` vì tái sử dụng runner W3. Full smoke tuần 3 còn được lưu tại `artifacts/smoke-20261108084854-4053705f12f448318018da1394c8f2f4/report.json`.

### 8.2. Commit đã có trong lịch sử checkout

| Tuần | Ngày commit | Nhánh làm việc/bàn giao | Commit | Nội dung |
|---|---|---|---|---|
| W1 | 20/10/2026 | `linh_tuan_1` | `7463171` | `linh_commit`: tests và tài liệu tiếp quản |
| W2 | 30/10/2026 | `linh/w2-linh-01-analytics` | `78acbf6` | `feat(spark): implement week-two analytics and scoring` |
| W3 | 08/11/2026 | `linh/w3-linh-01-hdfs` | `a38d51d` | `linh commit week 03` |
| W4 | 16/11/2026 | `linh/w4-linh-01-correctness` | `d818855` | `test(spark): strengthen week-four correctness checks and handoff docs` |

Một số nhật ký tuần vẫn giữ câu “chưa commit/push” tại thời điểm triển khai. Bảng trên cập nhật việc **đã có commit trong lịch sử local** khi lập báo cáo; không dùng những câu nhật ký cũ để kết luận rằng code hiện chưa commit. Trạng thái push/merge không được xác minh mới trong phiên tổng hợp.

## 9. Giới hạn và công việc còn chờ

| Nội dung | Phần đã thực hiện | Phần còn cần xác nhận/phối hợp |
|---|---|---|
| Review tuần 1 và tuần 4 | Tests, tài liệu và evidence đã chuẩn bị | Trọng/Nhân review; cập nhật checkpoint khi đủ tiêu chí |
| Serving analytics | Producer schemas, callbacks và output Parquet đã có | Store/CQL/endpoints của Nhân và regression tích hợp theo `BL-LINH-02` |
| LIVE | Đã kiểm sample pseudonymize bằng Spark | Ghép collector của Thành và kiểm chứng toàn luồng LIVE |
| CP3/CP4 | Linh có evidence HDFS/retry/restart cho phạm vi producer | Nghiệm thu chung, clone sạch máy thứ hai, demo và các module còn lại; checkout hiện vẫn ghi TODO |
| Backlog normalization | Ba vấn đề `BL-THANH-19/20/21` đã có sửa và regression từ W2 | Nhãn backlog vẫn OPEN; cần đồng bộ trạng thái theo quy trình review |

Các giới hạn kỹ thuật đã ghi trong tài liệu bàn giao:

- Watermark dựa trên event time; chờ theo đồng hồ không tự làm cửa sổ cuối finalize khi input đứng yên.
- Dedup có horizon giới hạn, không lưu mọi event ID vĩnh viễn.
- Retry activity đã được kiểm chứng sau ghi thành công, nhưng không có cam kết exactly-once xuyên tất cả sink.
- Số editor duy nhất là ước lượng; risk dùng rule/caps cấu hình và nhận diện revert theo các mẫu tiếng Anh đã nêu trong contract.
- Môi trường kiểm thử là demo một node, HDFS replication 1; chưa là nghiệm thu HA, benchmark production hoặc độ trễ LIVE toàn hệ thống.

## 10. Nhật ký tổng hợp và nguồn tham chiếu

- **25/11/2026:** Đọc bốn plan, checkpoint/backlog, danh mục file và lịch sử commit tại `d818855`; đối chiếu các report CP0/HDFS và log review W4 trên máy. Tạo báo cáo theo yêu cầu, không chạy lại pipeline hoặc thay đổi trạng thái nghiệm thu các tuần.
- Nguồn chi tiết: [W1-LINH-01](../plans/W1-LINH-01.md), [W2-LINH-01](../plans/W2-LINH-01.md), [W3-LINH-01](../plans/W3-LINH-01.md), [W4-LINH-01](../plans/W4-LINH-01.md).
- Nguồn kỹ thuật chuẩn: [contracts](../contracts.md) và [processing README](../../processing/README.md). Trạng thái thực thi: [checkpoints](../checkpoints.md); phụ thuộc và findings: [backlog](../backlog.md).
