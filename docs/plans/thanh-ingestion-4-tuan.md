Trạng thái: ACTIVE · Owner: Thành · Reviewer: Trọng, Linh · Liên quan: W1–W4-THANH-01

# Ingestion/Kafka/Replay — lộ trình của Thành

Lộ trình tổng quan để theo dõi phần việc của Thành; trạng thái chính thức ở [checkpoints](../checkpoints.md), các quyết định và việc chưa có lịch ở [backlog](../backlog.md). Trước khi triển khai mỗi checkpoint, tạo plan riêng `docs/plans/<ID>.md` theo AGENTS.md; plan đó là nơi lưu thiết kế chi tiết, nhật ký và evidence. Tài liệu này không thay đổi contract. Nguồn: [plans.md](../../plans.md), [contracts.md](../contracts.md), [spike EventStreams](../thanh/ingestion-spike.md).

## Mục tiêu và phạm vi

Đưa nguồn LIVE từ Wikimedia qua Kafka theo contract hiện có; tăng độ tin cậy của collector và replay; bàn giao hướng dẫn, kiểm thử và demo. Phần việc thuộc `ingestion/`, `replay/`, test và tài liệu module của Thành. Spark, serving, dashboard và cấu hình tích hợp chung do các owner tương ứng phụ trách. Tuần 4 ưu tiên sửa lỗi và bàn giao, không bổ sung tính năng.

## Bức tranh tiến độ

| Checkpoint | Trạng thái chính thức | Kết quả hiện có / đích tiếp theo | Phụ thuộc và reviewer |
|---|---|---|---|
| [W1-THANH-01](W1-THANH-01.md) | REVIEW | Có replay, envelope, fixture LIVE đã pseudonymize và evidence CP0; còn review. | Trọng, Linh |
| [W2-THANH-01](W2-THANH-01.md) | REVIEW | Collector LIVE → Kafka, reconnect và counters; evidence và giới hạn ở plan W2. | W1; Trọng, Linh review |
| [W3-THANH-01](W3-THANH-01.md) | REVIEW | Đã kiểm thử outage/recovery, replay timing và recording; evidence ở plan W3. | W2; Linh review |
| [W4-THANH-01](W4-THANH-01.md) | REVIEW | Đã kiểm thử ingestion/replay trên EC2; còn review và demo phối hợp với nhóm. | CP3; Trọng, Mạnh và nhóm |

Các ô trên phản ánh checkpoint cá nhân, không tự suy ra CP2–CP4 của cả nhóm đã đạt. Tuần là giai đoạn kế hoạch, không phải khẳng định lịch thực tế. Ước lượng ban đầu theo checkpoint: 10–15 giờ mỗi tuần, gồm review và dự phòng; điều chỉnh sau plan chi tiết.

## W2 — LIVE collector

- [ ] Tạo `W2-THANH-01.md`: xác định phạm vi, baseline, thiết kế ACK/resume, các quyết định liên nhóm và test trước khi code.
- [ ] Xây parser SSE và collector LIVE: `PIPELINE_MODE=LIVE`, User-Agent, envelope chung, publish Kafka, counters log JSON mỗi 30 giây, reconnect/backoff có jitter và giới hạn, shutdown có kiểm soát. Giữ `Last-Event-ID` nguyên văn khi resume; chi tiết timeout và batching chốt ở plan W2.
- [ ] Kiểm tra từng ACK/thất bại và chỉ tiến vị trí resume qua dãy event đã được xác nhận an toàn; không suy ra `flush()` thành công nghĩa là mọi message đã thành công. Kiểm thử lỗi và ACK ngoài thứ tự.
- [ ] Kiểm thử SSE/collector, regression replay và integration Kafka; chạy LIVE ít nhất 20 phút, chứng minh có reconnect và record trong Kafka. Ghi điều kiện, lệnh và output tái hiện được trong plan W2.
- [ ] Cập nhật README module, backlog và checkpoint theo evidence; gửi Trọng/Linh review. Không tự đánh DONE khi thiếu tiêu chí hoặc review cần thiết.

Phạm vi dự kiến: `ingestion/collector/app/main.py`, các module parser/collector mới trong cùng thư mục, `ingestion/collector/tests/`, `ingestion/envelope.py` và tests khi cần, `replay/requirements.txt` nếu thêm dependency HTTP. Tên file và chi tiết interface sẽ chốt tại plan W2. Theo dõi BL-THANH-16 về đếm parse error.

## W3 — Độ bền và replay

- [ ] Tạo `W3-THANH-01.md`, xác định tiêu chí lỗi, phạm vi quan sát và test cô lập trên nền W2.
- [ ] Kiểm thử Kafka outage/recovery: đối chiếu ID duy nhất, bản trùng và khả năng thiếu trong điều kiện test; ghi rõ giới hạn, không kết luận bảo đảm tuyệt đối từ một lượt test.
- [ ] Mở rộng replay theo thời gian gốc (`--timing original`) và test timestamp thiếu/không tăng; giữ tương thích hành vi CLI và fixture CP0 hiện có.
- [ ] Thiết kế/chạy `--record` cho nguồn dự phòng demo: xác định entrypoint, cách pseudonymize và test chặn username/IP thật trong fixture hoặc dữ liệu commit.
- [ ] Phối hợp Linh đo backlog và thời gian Spark bắt kịp, gồm late data/watermark; chạy regression, cập nhật README và evidence, gửi review.

Đầu ra và evidence thực tế, bao gồm `--record` và `--timing original`, nằm ở [plan W3](W3-THANH-01.md). Checklist trên là phạm vi ban đầu; trạng thái từng bước và review xem trong plan W3.

## W4 — Ổn định và bàn giao

- [ ] Tạo `W4-THANH-01.md`; rà soát lỗi và nợ kỹ thuật W1–W3 liên quan nghiệm thu.
- [ ] Sửa lỗi trong phạm vi ingestion/replay, chạy regression và hoàn thiện runbook trong README module.
- [ ] Chạy LIVE ít nhất 30 phút trên máy thứ hai theo lộ trình Thành; ghi SHA, môi trường, lệnh, thời lượng, kết quả reconnect/Kafka và giới hạn. CP4 chung yêu cầu LIVE ≥15 phút; kết quả cá nhân không tự đóng CP4.
- [ ] Phối hợp Mạnh demo nguồn LIVE và phương án dự phòng REPLAY; bàn giao evidence cho Trọng và nhóm review.
- [ ] Cập nhật checkpoint, backlog và kết quả plan khi đủ evidence; giữ các phụ thuộc nhóm chưa hoàn thành ở trạng thái thực tế.

## Giao diện và quyết định cần phối hợp

- Kafka payload giữ dữ liệu nguồn và thêm `ingested_at`, `collector_version`; key theo wiki/page như [contract](../contracts.md#kafka--thành--linh). Không đổi ID/event time của replay. Thay đổi contract cần producer và consumer review; nếu phát hiện mâu thuẫn contract thì dừng phần liên quan và hỏi hai bên trước khi code.
- Allowlist, Kafka DLQ, định dạng version và giới hạn delivery/resume còn theo [BL-THANH-01–04](../backlog.md#cần-nhóm-quyết-định). Đây là các đề xuất đang chờ, không coi là quyết định đã chốt. BL-THANH-05 cần Linh/Nhân/Mạnh chốt ý nghĩa metric.
- `replay` giữ mặc định CLI và exit code hiện có: 0 thành công, 1 lỗi gửi/flush, 2 dùng sai, 3 không kết nối được broker; nếu dự kiến thay hành vi phải làm rõ trong plan và tài liệu.
- Trọng sở hữu Compose, Makefile, scripts, shared config và tích hợp; cần thay đổi thì mở/cập nhật backlog cho owner. `restart: on-failure`, forward `COLLECTOR_VERSION` và retention raw cho topic mới đã có theo W2/W3 của Trọng; không đồng nghĩa LIVE collector đã hoạt động.
- Linh sở hữu Spark/consumer; phối hợp contract, canary, temporary account và late data. Nhân/Mạnh phụ trách serving/dashboard; không dùng readiness UI làm bằng chứng độc lập rằng collector đang nhận dữ liệu.
- Dữ liệu LIVE có thể chứa danh tính; không commit username/IP thật trong log, fixture hay tài liệu. Bronze/raw có thể giữ payload nguồn theo contract; pseudonymization không phải anonymization tuyệt đối.

## Rủi ro và kiểm chứng

| Rủi ro | Cách theo dõi |
|---|---|
| SSE ngắt, Kafka lỗi hoặc ACK thất bại | Test reconnect, retry và vị trí resume với lỗi/ACK ngoài thứ tự; W2–W3 lưu evidence, không tuyên bố exactly-once. |
| Resume muộn hơn watermark hoặc giới hạn lưu giữ nguồn | Phối hợp Linh; ghi điều kiện và giới hạn đo, theo dõi BL-THANH-04. |
| Dung lượng raw và recording | Theo dõi retention/dung lượng; chỉ dọn đúng môi trường test đã xác định, không mặc định xóa volume dev. |
| Lộ dữ liệu LIVE | Pseudonymize mẫu trước khi commit và có test chặn username/IP; không log payload raw. |
| Khác biệt môi trường kiểm thử | Theo dõi BL-THANH-38: test Compose Windows bỏ biến `PROGRAMFILES`; workaround và evidence ở plan W2. |
| Phụ thuộc quyết định nhóm hoặc owner khác | Link backlog tương ứng; làm phần độc lập nhưng không tự sửa module ngoài ownership hay tự đóng quyết định. |

## Nhật ký

- 2026-11-23 — Cập nhật lộ trình tổng W2–W4 từ checkpoint, contract và khảo sát code; phân biệt phần hiện có, evidence cá nhân và cổng nghiệm thu chung. Chưa triển khai code hoặc thay trạng thái checkpoint.
- 2026-11-23 — W2 chuyển REVIEW sau kiểm chứng; chi tiết/evidence ở [W2-THANH-01](W2-THANH-01.md), chờ Trọng/Linh review.
- 2026-11-23 — W3 chuyển REVIEW sau kiểm chứng; chi tiết/evidence ở [W3-THANH-01](W3-THANH-01.md), chờ Linh review và phụ thuộc W2.
- 2026-11-23 — W4 chuyển REVIEW sau kiểm thử và dọn EC2; giới hạn, evidence và phần chờ nhóm ở [W4-THANH-01](W4-THANH-01.md).
