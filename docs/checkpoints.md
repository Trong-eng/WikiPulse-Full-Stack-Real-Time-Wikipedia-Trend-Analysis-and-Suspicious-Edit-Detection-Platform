# Checkpoints — WikiPulse

Ngày tạo: 11/10/2026. Tuần tính từ ngày kickoff do nhóm chọn. Chỉ cập nhật DONE khi đã đạt tiêu chí và có evidence; chưa tự đánh dấu phần việc của các thành viên đã hoàn thành vì có scaffold.

## Cổng nghiệm thu chung

| Mốc | Owner nghiệm thu | Trạng thái | Tiêu chí | Bằng chứng |
|---|---|---|---|---|
| CP0 | Trọng | DONE | REPLAY thật qua Kafka/Spark/3 tầng Parquet/Cassandra/API/Overview | docs/trong/verification.md; smoke status=passed ngày11/10/2026 |
| CP1 | Cả nhóm; Trọng tổng hợp | TODO | Người khác clone/chạy lại CP0; nhận module/contracts/test đầu tiên | PR và log máy thứ hai |
| CP2 | Cả nhóm | TODO | LIVE/REPLAY, windows/risk/trend, UI thật, HDFS khởi động | Fixture assertions + LIVE logs |
| CP3 | Cả nhóm | TODO | E2E HDFS; late data/restart/retry/Gold finalized | Logs + output checks |
| CP4 | Cả nhóm | TODO | Clone sạch máy thứ hai; replay pass; LIVE ≥15 phút; 4 trang + docs | Release checklist/demo |

## Tuần 1 — Trọng thực hiện core và khung

| ID | Owner | Reviewer | Phụ thuộc | Đầu ra / tiêu chí nghiệm thu | Giờ | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|---|---|
| W1-TRONG-01 | Trọng | Cả nhóm | Không | Monorepo, plans.md, contracts v0.1, ownership/checkpoints | 2 | DONE | plans.md; docs/contracts.md; bảng này |
| W1-TRONG-02 | Trọng | Thành, Nhân | 01 | Config/env/Compose core, topic và CQL init, Docker ARM64 | 3 | DONE | Build images ARM64; Compose config; E2E pass |
| W1-TRONG-03 | Trọng | Linh, Nhân | 01,02 | Ghép minimal replay/Spark/Parquet/Cassandra/API hoạt động | 3 | DONE | Activity5/1; Bronze11/invalid2/Silver7/Gold2; smoke pass |
| W1-TRONG-04 | Trọng | Mạnh | 02,03 | Makefile, fixtures, smoke cô lập, README và hướng dẫn bàn giao | 2 | DONE | README; make test84passed; lint/config pass |
| W1-TRONG-05 | Trọng | Cả nhóm | 04 | Nghiệm thu kỹ thuật CP0, code review và bộ tài liệu handoff | 2 | DONE | docs/trong/verification.md; team tự review contracts/rerun ở CP1 |

## Đầu việc 4 tuần của 5 role

Đây là việc nhóm cần nhận và hoàn thiện; scaffold là điểm xuất phát. Mỗi owner tự quản tests/docs module. Giờ bên dưới đã gồm review và dự phòng.

| ID | Owner | Reviewer | Phụ thuộc | Đầu ra / điều kiện DONE | Giờ | Trạng thái | Evidence |
|---|---|---|---|---|---|---|---|
| W1-THANH-01 | Thành | Trọng, Linh | contracts | Tiếp quản replay/topics, kiểm tra fixture/key/producer errors | 10–15 | REVIEW | [docs/plans/W1-THANH-01.md](plans/W1-THANH-01.md) |
| W1-LINH-01 | Linh | Trọng, Nhân | contracts | Tiếp quản schema/validation/ID/Silver/activity, đọc/test sample | 10–15 | TODO | PR + sample output |
| W1-NHAN-01 | Nhân | Trọng, Mạnh | contracts | Tiếp quản CQL/sink/API, review khóa và API schema | 10–15 | REVIEW | docs/serving-review.md; api tests 33 passed (4 integration trên Cassandra thật); CP0 chạy lại trên Windows ngày 15/10/2026 |
| W1-MANH-01 | Mạnh | Trọng, Nhân | API contract | Tiếp quản 4 trang/client/Overview, chạy CP0 máy mình | 10–15 | REVIEW | [docs/plans/W1-MANH-01.md](plans/W1-MANH-01.md) |
| W2-TRONG-01 | Trọng | Linh | CP1 | HDFS profile, readiness/config, hai lần tích hợp | 10–15 | TODO | Full profile start logs |
| W2-THANH-01 | Thành | Trọng, Linh | W1-THANH | SSE LIVE, backoff/reconnect/counters, chung envelope | 10–15 | TODO | LIVE Kafka records + reconnect test |
| W2-LINH-01 | Linh | Trọng, Nhân | W1-LINH | Windows 1m/5m-slide1m, dedup/late, features/risk/trend | 10–15 | TODO | Golden fixture tests |
| W2-NHAN-01 | Nhân | Linh, Mạnh | W2-LINH contract | Trends/suspicious/detail, query keys/capacity/errors | 10–15 | TODO | Endpoint + idempotent sink tests |
| W2-MANH-01 | Mạnh | Nhân | API examples | Hoàn thiện 4 trang/filter/empty/error/provisional | 10–15 | TODO | UI acceptance evidence |
| W3-TRONG-01 | Trọng | Linh | CP2 | Tích hợp full HDFS, persistence; K8s/monitor skeleton | 10–15 | TODO | Full E2E logs |
| W3-THANH-01 | Thành | Linh | W2-THANH | Replay timing/speed, Kafka outage, fixtures regression | 10–15 | TODO | Producer/replay recovery tests |
| W3-LINH-01 | Linh | Nhân | HDFS full | Ba tầng HDFS, partitions, Gold finalized/late/checkpoint | 10–15 | TODO | Parquet reads + restart checks |
| W3-NHAN-01 | Nhân | Trọng, Mạnh | W2-NHAN | Retry/upsert, latest window/detail, capacity test | 10–15 | TODO | Correct row counts after retry |
| W3-MANH-01 | Mạnh | Trọng | CP2 | E2E hai mode, privacy/freshness/API outage, demo flow | 10–15 | TODO | Regression checklist |
| W4-TRONG-01 | Trọng | Cả nhóm | CP3 | Freeze, clone sạch máy khác, release candidate, limitations | 10–15 | TODO | CP4 evidence |
| W4-THANH-01 | Thành | Trọng | CP3 | Sửa ingestion/replay bugs, runbook và demo nguồn | 10–15 | TODO | Final tests/docs |
| W4-LINH-01 | Linh | Trọng, Nhân | CP3 | Correctness fixes, công thức/giới hạn, golden results | 10–15 | TODO | Final tests/docs |
| W4-NHAN-01 | Nhân | Trọng, Mạnh | CP3 | Serving/API regression, OpenAPI/data dictionary/runbook | 10–15 | TODO | Final tests/docs |
| W4-MANH-01 | Mạnh | Cả nhóm | CP3 | Regression/demo video/README verification/release checklist | 10–15 | TODO | Demo + acceptance report |

## Quy tắc cập nhật

TODO → IN_PROGRESS → REVIEW → DONE; BLOCKED cần mô tả nguyên nhân/owner tháo gỡ. Evidence phải có PR/commit hoặc lệnh và output tái hiện được. Checkpoint đổi khi có bằng chứng, không đổi chỉ vì hết tuần. Đổi contract phải được producer/consumer review. Bị chặn quá một ngày dùng fixture/contract để tiếp tục việc độc lập. Tuần 4 không bổ sung tính năng.
