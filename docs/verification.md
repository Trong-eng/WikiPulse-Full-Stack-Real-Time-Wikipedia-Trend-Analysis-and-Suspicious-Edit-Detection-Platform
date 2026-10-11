# CP0 / Trọng tuần1 — bằng chứng kiểm chứng

Ngày11/10/2026 (Asia/Ho_Chi_Minh). Các kết quả dưới đây là chạy thật, không seed serving hoặc tự tính expected bằng code pipeline.

## Kiểm thử

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Lightweight suite | make test | 84 passed,9 deselected (Spark/integration tách riêng) |
| Spark thực | Docker Python3.11/Java17/PySpark3.5.6: pytest processing/spark/tests -q | 16 passed |
| Lint | make lint | All checks passed |
| Compose | make config | Exit0 |
| End-to-end | .venv/bin/python scripts/smoke_test.py --keep | status=passed |

Host tests có warnings từ Starlette/AnyIO, Streamlit/NumPy/Altair; không có failures. Integration opt-in; host không có PySpark nên không dùng host skip làm bằng chứng Spark. Spark suite chạy trong container có JVM.

## Real smoke

Run ID: `smoke-20261011041433-785702442fdb4d8b9d15edca5c1a4d6e`.

- Kafka nhận11 records fixture qua replay producer thật.
- Bronze/raw11, invalid2, Silver7 sau duplicate/canary exclusion.
- Cassandra/API window2026-01-01T00:00Z: enwiki5 events/5edits/1anon/1bot; viwiki1 event/1new page.
- Gold/window00:00 có đúng2 rows sau event00:12:10 tiến watermark10m.
- AppTest chạy **trong dashboard image, gọi API của stack thật**; chọn historical window đúng, cả5 metrics của haiwiki khớp fixture. SystemStatus xác nhận HTTP200/Cassandra ready.
- API health và Streamlit HTTPhealth pass; ba endpoint deferred trả501.
- Stack test có project/namespace/volumes riêng; đã dọn containers/volumes sau nghiệm thu. Evidence files còn trong artifacts, không xóa dev data.

Full logs (local, gitignored): `artifacts/smoke-20261011041433-785702442fdb4d8b9d15edca5c1a4d6e/{report.json,commands.log,services.log}`. Đường link/ports55002/55003 của smoke chỉ tồn tại khi giữ stack; không phải URL demo cố định. `make smoke` tạo run mới và tái kiểm chứng được.

## Review và sửa lỗi đã xác minh

Fresh code review kiểm tra scope/correctness. Đã sửa allowlist/UI local API port, pin endpoints/topics cho smoke, UUID namespace tránh collision, kiểm tra Overview thật, fail-loud khi tải Kafka jars, structured application logs. Lần startup đầu tìm ra Kafka UID1000 thiếu quyền named volume mới; Compose thêm init-kafka-volume sửa ownership trong đúng volume WikiPulse rồi clean smoke pass.

Regression timestamp API `Z` so với fixture `+00:00` đã kiểm chứng bằng AppTest: selection qua formatted index hoạt động và không chọn nhầm window mới hơn.

## Giới hạn nghiệm thu

CP0 DONE là khung activity-only REPLAY/local Parquet. CP1 vẫn TODO: thành viên khác cần clone/chạy lại và review contracts. LIVE, HDFS thực, trend/risk/detail, Kubernetes deployment và metrics chưa được nghiệm thu; không đánh dấu các tuần sau DONE. Checkpoint tuần1 của4người khác là việc tiếp quản/thực hiện của họ, không tự ghi DONE.

## Demo trong workspace

Sau smoke đã chạy `make up` và replay trên project mặc định `wikipulse`. Kafka/Cassandra/API/dashboard healthy; Spark có5queries đang hoạt động. API localhost:18000 trả window00:00/enwiki5events và window00:12/enwiki1event đúng dữ liệu mẫu; dashboard localhost:8501. Muốn xem số liệu5events chọn cửa sổ01/01/2026 00:00 UTC. Dừng demo bằng `make down` (giữ volumes).
