Trạng thái: DONE · Owner: Linh · Reviewer dự kiến: Nhân (chưa ghi nhận review người) · Liên quan: W3-LINH-01, BL-LINH-03, BL-TRONG-01

## Mục tiêu

Đưa Bronze/Silver/Gold lên HDFS; kiểm chứng partitions, late data, Gold finalized và khôi phục checkpoint theo [checkpoints](../checkpoints.md), [contracts](../contracts.md) và [kế hoạch tổng](../../plans.md).

## Phạm vi / Không làm

Phiên 2026-11-04 chuẩn bị môi trường và kế hoạch thực hiện. Lab HDFS nằm trong module processing, phục vụ kiểm thử độc lập của Linh. Profile full dùng chung do Trọng sở hữu; lab không thay thế nghiệm thu full E2E/CP3. Không thay đổi scoring, contract hoặc code Cassandra/API.

Phiên 2026-11-08 thực hiện W3 trên profile full đã có ở main `312c086`. Acceptance dùng Kafka thật, Hadoop 3.4.3, Cassandra activity thật và production query starter; chạy nhiều tiến trình Spark cùng checkpoint qua các phase. Analytics W2 vẫn dùng Parquet do Nhân chưa có sink; không coi thiếu sink W2 là blocker cho correctness HDFS của Linh.

## Các bước

- [x] Đọc GitHub main và kiểm tra commit tuần 2 làm nền.
- [x] Kiểm tra venv, Docker, Spark/Java và baseline tests.
- [x] Chuẩn bị lab NameNode/DataNode replication 1, volumes bền và Spark client; kiểm tra ghi/đọc Parquet qua HDFS, giữ dữ liệu sau restart.
- [x] Triển khai và kiểm thử pipeline thật ghi Bronze/raw, Bronze/invalid, Silver/events, Gold/activity và Gold/trends trên HDFS; xác nhận partitions UTC theo contract.
- [x] Fixture theo phase: duplicate qua batch, late trong cửa sổ mở, tiến watermark, quá muộn sau finalized; so golden results độc lập.
- [x] Restart Spark với cùng RUN_ID/checkpoints HDFS; xác nhận offsets/state khôi phục, Silver không tăng do duplicate, Gold không bị ghi lặp.
- [x] Ghép full stack của Trọng và activity sink hiện có; kiểm thử retry sau ghi thành công, bàn giao evidence và cập nhật README. Sink analytics W2 của Nhân theo BL-LINH-02, ngoài nghiệm thu producer W3.

## Quyết định

- Nhánh `linh/w3-linh-01-hdfs` bắt đầu từ W2 `78acbf6` ngày 04/11; ngày 08/11 đã fast-forward main `312c086`, gồm cả W2 Linh và profile full của Trọng.
- Venv hiện có ở `D:\bigdata\.venv`; dùng `..\.venv\Scripts\python.exe` từ root repo. Chạy Spark/Java trong Linux container, không cần cài Hadoop/Java trực tiếp lên Windows.
- Dùng namespace mới cho lab; DATA_BASE_PATH và SPARK_CHECKPOINT_PATH là hai URI HDFS riêng. Không tái sử dụng checkpoint/schema tuần 1.
- Phụ thuộc profile full ghi ngày 04/11 ở [BL-LINH-03](../backlog.md#trọng) đã được gỡ bởi `312c086`. Giữ lab cũ và volumes; nghiệm thu W3 dùng profile chung Hadoop 3.4.3, không dùng lab 3.4.1.
- Production query starter tuần 2 đã hỗ trợ URI HDFS. W3 bổ sung runner nghiệm thu, fixture/golden results và runbook thay vì thay công thức hoặc schema đang đúng contract.

## Nhật ký

- 2026-11-08 — Người dùng yêu cầu thực hiện tuần 3. Cất setup vào stash dự phòng `linh-w3-prep-before-main-20261108`, fast-forward main `312c086`, áp dụng lại setup và giải quyết conflict backlog giữ cả hai bên. Thiết kế fixture UTC qua nửa đêm; duplicate trong/sau restart, late trong horizon, chốt watermark, too-late + fresh; inject lỗi sau upsert activity thật để xác minh retry tổng tuyệt đối. Không commit/push trong phiên này.

- 2026-11-04 — Đã fetch và xác minh GitHub: main `ca3d192`, nhánh W2 `78acbf6`. Tạo nhánh W3 từ W2; Docker Desktop ban đầu tắt, đã khởi động. Chỉ chuẩn bị môi trường theo yêu cầu, chưa commit/push.
- 2026-11-04 — Build `wikipulse-spark:w3-lab`, tải `apache/hadoop:3.4.1`; hai daemon healthy, 1 live DataNode. Probe ghi/đọc và đọc lại sau restart đều pass. Baseline lần đầu 65 pass/1 fail vì `fs.defaultFS` trỏ HDFS còn fixture tạo file local; chạy lại với `HADOOP_CONF_DIR=/tmp/wikipulse-no-hadoop-conf` đạt 66 pass. Đây là tách cấu hình môi trường test, không sửa logic nghiệp vụ. Lệnh đúng đã ghi trong README.

## Kết quả

**Đã hoàn tất phạm vi producer Spark/HDFS của Linh ngày 08/11/2026.** CP3 toàn nhóm và phần của các owner khác chưa được nghiệm thu. Code/tài liệu đang ở working tree trên nền `312c086`, chưa commit/push.

| Kiểm chứng cuối | Kết quả | Evidence |
|---|---|---|
| W3 Kafka → production Spark → HDFS/Cassandra activity | 7/7 phase passed, 9 query IDs giữ nguyên qua JVM mới; run IDs thay đổi | `artifacts/w3-20261108084619-0608715eade6/report.json` |
| Full smoke chung | passed; UI/API/activity/analytics Parquet; recreate HDFS + 9 checkpoint phục hồi | `artifacts/smoke-20261108084854-4053705f12f448318018da1394c8f2f4/report.json` |
| Spark regression | 66 passed, 53,07 giây | `artifacts/linh-w3/spark-tests.log` |
| Unit Windows | 138 passed, 57 deselected, 2 dependency warnings | `artifacts/linh-w3/unit-windows.log` |
| Bootstrap shell POSIX | 5 passed trong Linux container | `artifacts/linh-w3/bootstrap-linux.log` |
| Compose core/full | 2 cấu hình pass với env-file trống trên Windows | `artifacts/linh-w3/compose-validation.json` |
| Ruff, whitespace, links | pass | `artifacts/linh-w3/validation.log` |

Hai file test có giả định POSIX (`test_hdfs_bootstrap.py`, `test_deployment.py` dùng `/dev/null`) được tách khỏi lượt Windows. Năm test bootstrap chạy thực sự trong Linux; hai kiểm tra deployment được thực hiện bằng Compose CLI và env-file trống thay cho `/dev/null`. Không ghi nhầm thành 145 pytest passed trên Windows.

Kết quả golden cuối: Bronze 13, invalid 2, Silver/events 6, suspicious 2, Gold activity 2 và Gold trends 10. Cửa sổ mục tiêu `enwiki/2026-01-01T23:59:00Z/page_key=10` có 3 edits, 3 unique editors, abs delta 650, trend score 0.08375. Activity vẫn 3 sau lỗi được inject **sau khi** Cassandra đã upsert thành công và replay batch thất bại. Gold chưa xuất hiện ở initial/late/recovered, chỉ có sau clock event tiến watermark; too-late và idle restart không đổi kết quả. Fresh event sau restart vẫn được xử lý, chứng minh pipeline đã tiêu thụ đợt dữ liệu mới.

HDFS partition paths và giá trị UTC đã kiểm tra cho cả ba tầng. Silver đi qua `2026-01-01/23` và `2026-01-02/0`; Gold trends có cửa sổ bắt đầu ở ngày trước. Invalid JSON không có event time dùng Kafka timestamp cho partition theo contract. Hai lần recreate NameNode/DataNode giữ named volumes, mỗi phase dùng một JVM mới và checkpoint HDFS cũ; Bronze không lặp Kafka coordinates, Silver/Gold không lặp logical keys.

Lệnh tái hiện nằm ở [processing README](../../processing/README.md#week-three-hdfs-acceptance). Source fixture ở `processing/spark/tests/fixtures/week_three/`, expected độc lập ở `week_three_expected.json`; runner ở `processing/spark/acceptance/`. Gói bàn giao `artifacts/linh-w3-evidence-20261108.zip` chứa reports/logs và snapshot source, không đưa vào Git.

Nhật ký nghiệm thu 08/11: lần đầu dừng vì Compose v5 `--wait` coi one-shot init exit 0 là không running; runner sửa thành đợi daemon rồi chạy init riêng. Lần hai phát hiện Gold partitioned chưa có data file trước watermark không thể infer schema; reader nghiệm thu dùng schema rõ ràng, không đổi query production. Lần ba đạt cả 7 phase. Giữ log hai lần đầu ở `artifacts/w3-20261108083533-70449c336b04/` và `artifacts/w3-20261108084317-3291d2145a41/`.

Các project test tự cleanup đúng volumes của mình; lab chuẩn bị ngày 04/11 vẫn giữ containers/volumes đang dừng. `.venv`, image và stash dự phòng được giữ. Không xóa dữ liệu dev. Sink analytics Cassandra/API vẫn chờ Nhân (BL-LINH-02); collector LIVE chờ Thành. Không tuyên bố exactly-once xuyên nhiều sink, HA hoặc tải LIVE đã được nghiệm thu.

### Chuẩn bị môi trường ngày 04/11/2026

Đã chuẩn bị môi trường phát triển độc lập của Linh ở phiên trước. Khi đó chưa nghiệm thu W3-LINH-01 hay CP3. Lệnh bật lại lab ở [processing README](../../processing/README.md#week-three-development-environment).

| Kiểm tra | Kết quả | Evidence trong `artifacts/linh-w3-prep/` |
|---|---|---|
| Host | Python 3.11.5; pip check không có dependency lỗi; pytest 8.3.5, Ruff 0.11.2, PyYAML 6.0.2 | `environment.json` |
| Docker | 29.1.3, Linux x86_64; 16 CPU, 12.388.077.568 byte RAM | `environment.json` |
| Runtime | Spark 3.5.6, Hadoop client 3.3.4; server Apache Hadoop 3.4.1 | `hdfs-write.log`, `hadoop-image.txt` |
| Build/config | Image lab build thành công, Compose config hợp lệ | `spark-build.log`, `validation.log` |
| HDFS | 1 live DataNode, 0 missing/corrupt blocks | `hdfs-report.txt` |
| Ghi/đọc | 2 dòng synthetic/tầng probe; namespace checkpoint riêng ghi/đọc được | `hdfs-write.log` |
| Persistence | Restart cả hai daemon, đọc lại đủ dữ liệu probe | `hdfs-restart.log`, `hdfs-read-after-restart.log` |
| Baseline Spark | 66 passed, 58,32 giây | `spark-tests-local.log` |
| Lightweight | 127 passed, 57 deselected, 2 deprecation warnings, 9,16 giây | `unit-tests.log` |
| Ruff / whitespace | Pass | `validation.log` |
| Sau kiểm tra | Lab đã stop, giữ named volumes; không có Spark probe đang chạy | `stop.log` |

Probe chuẩn bị dùng dữ liệu môi trường synthetic; bản thân probe không kiểm chứng schema/partition Gold thật hay checkpoint streaming. Các kiểm chứng này đã được thực hiện riêng ngày 08/11 như bảng kết quả trên.

Không cần cài thêm Java/Hadoop/PySpark trên Windows. Các lượt của Linh được kiểm chứng trên x86_64; evidence ARM64 của profile chung nằm ở W2-TRONG-01. Profile full hiện đã có, sink W2 của Nhân vẫn theo BL-LINH-02.
