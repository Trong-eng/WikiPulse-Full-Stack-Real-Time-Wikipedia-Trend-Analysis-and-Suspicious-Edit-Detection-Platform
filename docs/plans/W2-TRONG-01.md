Trạng thái: DONE · Owner: Trọng · Reviewer dự kiến: Linh; đã review độc lập bằng agent, chưa ghi nhận review người · Liên quan: W2-TRONG-01, BL-LINH-01, BL-THANH-09/10/11

## Mục tiêu

Profile HDFS `full` chạy được trên ARM64, readiness có kiểm tra thật và tích hợp producer W2 của Linh; giữ đường core local. Nguồn phạm vi: `plans.md`, `docs/contracts.md`, `storage/hdfs/README.md`; người dùng xác nhận triển khai, merge main và push GitHub ngày 05/11/2026.

## Phạm vi / Không làm

Compose/config, HDFS một NameNode/DataNode với volume riêng, scripts/test tích hợp và docs của Trọng. Không sửa module Linh/Nhân/Thành/Mạnh, không nhận nghiệm thu CP1/CP2 hoặc tuần 3 thay nhóm. File local `trong-misc.md` có sẵn không đưa vào commit việc này.

## Các bước

- [x] Fetch, fast-forward Linh `78acbf6` vào main, checkout `trong/w2-trong-01-hdfs-readiness`; baseline lightweight 127 passed.
- [x] Test trước cho readiness (thiếu/cũ/inactive/đủ query), bootstrap HDFS không format dữ liệu cũ và smoke isolation.
- [x] Hoàn thiện profile `full` + overlay chọn HDFS cho Spark; forward scoring/sink/version; readiness, volume và startup dependencies.
- [x] Mở rộng smoke chạy core/HDFS, kiểm Parquet và restart cùng namespace; chạy unit, lint, Compose config, Spark suite và hai lượt tích hợp.
- [x] Cập nhật docs/evidence và review độc lập; bàn giao bằng commit `feat(infra): add full HDFS profile and week-two integration` để merge/push theo yêu cầu.

## Quyết định

- Dùng checkout hiện có và branch đã được xác nhận; giữ nguyên thay đổi local ngoài phạm vi. Plan này là nơi duy nhất lưu thiết kế, nhật ký và kết quả theo AGENTS.md.
- Profile `full` chứa HDFS; overlay `docker-compose.hdfs.yml` chọn URI/dependencies cho Spark vì Compose profile không thay environment của một service. Không bật HDFS trên core mặc định.
- Chọn image Apache có manifest ARM64/AMD64, pin version/digest sau khi kiểm chứng. NameNode chỉ format volume trống, từ chối volume có dữ liệu nhưng thiếu VERSION. Readiness phân biệt NameNode RPC/safemode, DataNode và khả năng ghi/đọc lúc init.
- Tích hợp #1 là core + analytics mới; #2 là full HDFS + restart đọc lại dữ liệu/checkpoint. Đây là hai lượt kỹ thuật trong phiên, không giả là hai ngày nghiệm thu của nhóm. CP1 còn REVIEW/TODO theo backlog cũ; không chặn phát triển độc lập đã được người dùng yêu cầu.
- Rủi ro cần kiểm: profile tắt không kéo HDFS; env dev không rò vào smoke; không reuse Silver v0.1; không format lại khi restart; health không xanh với progress cũ/thiếu query. Tests thực thi script và Compose config, không chỉ so khớp nội dung file.

## Nhật ký

- 2026-11-05 — Người dùng cho phép triển khai, commit/merge và push; đã merge Linh, baseline 127 passed/57 deselected. Docker 29.2.1 ARM64 đang chạy, giữ nguyên các stack có sẵn.

- 2026-11-06 — Tiếp tục sau gián đoạn: HDFS smoke đầu thất bại vì reverse DNS trong Compose; tắt kiểm reverse DNS riêng môi trường demo theo Hadoop, thêm bounded wait cho DataNode registration (test RED→GREEN). Review độc lập không còn blocker khác; sửa test readiness bị ảnh hưởng bởi env host (RED→GREEN).

## Kết quả

Kiểm chứng ngày 05–06/11/2026, Docker 29.2.1 ARM64. Không thay đổi contract; không đánh DONE CP1/CP2 hay việc của owner khác. Hai lượt tích hợp kỹ thuật đã đạt, review người của Linh còn chờ.

| Lệnh tái hiện | Kết quả |
|---|---|
| `make test` | 145 passed, 57 deselected; 26 warnings dependencies có sẵn |
| `make lint` | All checks passed |
| `make config` và `make config-full` | exit 0 |
| `docker compose build spark api dashboard replay` | exit 0 |
| `docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q` | 66 passed |
| `.venv/bin/python scripts/smoke_test.py --no-build` | core passed |
| `.venv/bin/python scripts/smoke_test.py --hdfs --no-build` | HDFS passed, recreate hai node + phục hồi 9 checkpoint IDs |

Core: [report](../../artifacts/smoke-20261105092204-86df1fc77ae8435ebba5e60fb251fab1/report.json). HDFS: [report](../../artifacts/smoke-20261106155546-a983e8f164344fbe8fd812955b2637ce/report.json), [commands](../../artifacts/smoke-20261106155546-a983e8f164344fbe8fd812955b2637ce/commands.log). Artifacts là local/gitignored; tái hiện bằng lệnh trên sau build. Cả hai smoke đã tự cleanup đúng project của mình.

Kết quả trước/sau restart: Bronze 11, invalid 2, Silver 7, Gold activity 2; events 7, suspicious 3, trends provisional/finalized 2 trang đúng scores fixture. Tests RED→GREEN và log suites ở `artifacts/w2-trong/`. HDFS lần đầu fail reverse DNS đã được ghi lại, không bỏ qua thất bại.

Quyết định triển khai: giữ core local, opt-in HDFS overlay và image Apache 3.4.3 pin digest; tắt reverse DNS registration check chỉ cho mạng Compose riêng không có reverse DNS. Không tuyên bố production/HA hoặc nghiệm thu LIVE. Đã mở BL-TRONG-01 cho Linh cập nhật câu README về env forwarding theo ownership.
