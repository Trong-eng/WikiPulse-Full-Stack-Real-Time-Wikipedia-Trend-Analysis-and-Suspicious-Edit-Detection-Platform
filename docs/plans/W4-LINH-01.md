Trạng thái: REVIEW · Owner: Linh · Reviewer dự kiến: Trọng, Nhân · Liên quan: W4-LINH-01, CP3, BL-LINH-02

## Mục tiêu

Kiểm tra correctness, củng cố golden results và hoàn thiện tài liệu công thức/giới hạn để bàn giao phần Spark/analytics của Linh theo [checkpoints](../checkpoints.md). Phần độc lập đã thực hiện và đang REVIEW; nghiệm thu W4 cuối cùng còn chờ review và tích hợp theo CP3.

## Phạm vi / Không làm

Phạm vi gồm chuẩn bị môi trường, đối chiếu công thức với contract, bổ sung regression/golden assertions, chạy nghiệm thu HDFS cho late data/retry/restart và hoàn thiện tài liệu bàn giao. Tái sử dụng venv, Docker Linux và runner HDFS tuần 3. Không bổ sung tính năng, thay contract hoặc triển khai module của thành viên khác; giữ dữ liệu và volumes cũ.

## Các bước

- [x] Đối chiếu GitHub và tạo nhánh tuần 4 từ commit W3 `a38d51d`.
- [x] Kiểm tra dependency, Docker runtime, cấu hình Compose và baseline tests.
- [x] Rà soát golden results độc lập với code tính toán, bổ sung trường hợp thiếu nếu có.
- [x] Kiểm tra correctness và chạy regression liên quan; chưa phát hiện lỗi production cần sửa.
- [x] Hoàn thiện công thức, giới hạn và hướng dẫn tái hiện trong processing README.
- [ ] Khi CP3 và các module phụ thuộc sẵn sàng, kiểm chứng tích hợp và bàn giao final evidence cho Trọng/Nhân.

## Quyết định

- Nhánh `linh/w4-linh-01-correctness` bắt đầu từ W3 đã push, vì main `312c086` chưa chứa W3. Không bỏ phần W3 khi chuẩn bị W4; PR W4 cần phân biệt phần kế thừa khi W3 chưa merge.
- Venv: `D:\bigdata\.venv`, Python 3.11; Spark/Java chạy Linux container. Không cần cài PySpark, Java hay Hadoop lên Windows.
- Dùng analytics Parquet cho kiểm thử producer; Cassandra analytics/LIVE vẫn chờ Nhân/Thành. CP3 toàn nhóm chưa đạt, không chặn chuẩn bị và kiểm thử độc lập.
- Mỗi lần nghiệm thu HDFS dùng project/RUN_ID riêng do runner W3 sinh; không tái sử dụng checkpoints cũ cho schema/scoring khác.
- Các lệnh chuẩn bị và kiểm tra nằm tại [processing README](../../processing/README.md#week-four-development-environment).

## Nhật ký

- 2026-11-16 — Cải thiện sau review: đổi fixture metadata thành a/Zulu/namespace=2 và b/Alpha/namespace=1 cùng timestamp; kiểm tra title/namespace theo event_id ở cả hai thứ tự nhận. Sửa mục tiêu/phạm vi phản ánh phần W4 đã thực hiện và đường dẫn test trong README. Xác minh test bằng code đúng và giả lập lỗi ưu tiên title trước event_id chỉ trong bộ nhớ; cập nhật evidence sau kiểm tra. Chưa commit/push.
- 2026-11-16 — Bắt đầu thực hiện W4 theo yêu cầu: đối chiếu analytics/scoring với contract và golden W2/W3; bổ sung regression tổng hợp risk (bot/non-edit), ranh giới cửa sổ và metadata tie không phụ thuộc arrival order. Bổ sung công thức, ví dụ tính tay và giới hạn bàn giao trong processing README. Chạy lại Spark, lightweight, lint và acceptance HDFS trên project riêng.
- 2026-11-16 — Theo yêu cầu chuẩn bị môi trường: working tree ban đầu sạch; tạo nhánh từ `a38d51d`; venv Python 3.11.5 và pip check pass. Khởi động Docker Desktop đang tắt. Chưa commit/push.

## Kết quả

### Thực hiện tuần 4 ngày 16/11/2026

- Spark regression trước cải thiện sau review: **68 passed**, 73,45 giây (`artifacts/linh-w4/spark.log`). Hai test mới kiểm tra tổng hợp risk 60/50/0/0, đầu/cuối cửa sổ half-open, metadata tie và thứ tự nhận đảo ngược. Golden trend tính tay là 0.0335 và 0.023. Kết quả kiểm tra fixture sau cải thiện được ghi riêng bên dưới.
- Sau cải thiện review: chạy `processing/spark/tests/test_week_four.py` bằng cùng lệnh Docker bind-mount trong README, đạt **2 passed**, 13,70 giây (`artifacts/linh-w4/review-tests.log`). Fixture đặt thứ tự title/namespace ngược event_id; assert metadata `Alpha/1` ở cả hai thứ tự nhận và `NextWindow/0` ở cửa sổ kế tiếp.
- Kiểm tra khả năng bắt lỗi: giả lập trong bộ nhớ việc ưu tiên title trước event_id làm test thất bại đúng ở assertion `Zulu/2 != Alpha/1`; script kiểm chứng kết thúc exit 0 với `MUTATION_CHECK=passed` (`review-mutation.log`, script tái hiện `artifacts/linh-w4/review_mutation.py` chạy bằng Python trong cùng container bind-mount). Dòng `1 failed` trong log là kết quả mong đợi của code giả lập sai, không phải lỗi production. Ruff và whitespace pass, đường dẫn README tồn tại. Không cần chạy lại toàn bộ HDFS/lightweight vì thay đổi chỉ ở test và tài liệu.
- Lightweight: **138 passed, 59 deselected**, hai dependency deprecation warnings (`artifacts/linh-w4/unit.log`). Ruff toàn repo pass (`lint.log`); whitespace pass.
- Chưa phát hiện sai lệch công thức/schema so với contract trong phạm vi đã chạy; production logic giữ nguyên. Công thức và giới hạn đã ghi ở [processing README](../../processing/README.md#week-four-formulas-and-handoff-limits).
- Acceptance HDFS **7/7 phase passed**, 9 query checkpoint IDs giữ nguyên qua JVM mới, qua hai lần recreate HDFS; cleanup thành công (runner exit 0). Report mới: `artifacts/w3-20261116142755-9571ad62d2f7/report.json`; log tổng `artifacts/linh-w4/hdfs-acceptance.log`. Runner W3 được tái sử dụng cho regression W4, không đổi nhãn run ID. Bronze 13, invalid 2, Silver/events 6, suspicious 2, Gold activity 2, Gold trends 10; activity mục tiêu 3 và trend 0.08375 giữ nguyên sau retry/restart/too-late.
- Tích hợp analytics Cassandra/API và LIVE, CP3 toàn nhóm và review của Trọng/Nhân vẫn chờ. Không tự đánh dấu W4 DONE từ kiểm thử producer.
- Phần độc lập của Linh sẵn sàng review; checkpoint W4 chuyển REVIEW. Chưa commit/push. Evidence và source snapshot đóng gói tại `artifacts/linh-w4-evidence-20261116.zip`.

### Chuẩn bị môi trường

Môi trường sẵn sàng cho phần độc lập của Linh ngày 16/11/2026. Evidence chuẩn bị lưu tại `artifacts/linh-w4-prep/` (gitignored):

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Venv Python 3.11.5 | pip check pass | `pip-check.log` |
| Unit Windows | 138 passed, 57 deselected, 2 dependency deprecation warnings | `unit-windows.log` |
| Spark + bootstrap POSIX trên source hiện tại | 71 passed (66 Spark + 5 bootstrap), 58,72 giây | `spark-linux.log` |
| Compose full/lab | config --quiet pass | `compose.log` |
| Docker | 29.1.3, Linux x86_64, 16 CPU; hai volumes lab cũ còn nguyên | `docker.log` |
| Image runtime | Python 3.11.18, Spark 3.5.6, PyYAML 6.0.2 | `runtime.log` |

Docker Desktop đang chạy; hai daemon lab cũ vẫn dừng, không cần chiếm RAM khi chỉ làm golden/unit tests. Các container kiểm thử dùng `--rm`. Không cài thêm dependency vì môi trường hiện có đã đạt kiểm tra. Chưa chạy lại E2E HDFS hay LIVE trong phiên chuẩn bị. Chưa commit/push.

Kết quả tuần 3 giữ nguyên ở [W3-LINH-01](W3-LINH-01.md); không dùng kết quả cũ làm evidence chạy mới cho W4. CP3 còn TODO và W4 chưa hoàn thành.
