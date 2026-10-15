# W1-THANH-01 — Tiếp quản replay/topics, kiểm tra fixture/key/producer errors

Trạng thái: REVIEW · Owner: Thành · Reviewer: Trọng, Linh · Liên quan: [checkpoints](../checkpoints.md), lộ trình [thanh-ingestion-4-tuan](thanh-ingestion-4-tuan.md)

## Mục tiêu

Replay báo lỗi rõ ràng và có test đầy đủ. Có envelope Kafka dùng chung, sẵn sàng cho collector LIVE tuần 2. Có dữ liệu LIVE thật để thiết kế collector. CP0 chạy lại được trên Windows (CP1).

## Phạm vi / Không làm

- Làm: `ingestion/envelope.py`, `replay/`, fixture LIVE mẫu, spike EventStreams, README của replay.
- Không làm: sửa fixture CP0 (`tests/fixtures/recentchange.jsonl`, smoke đang phụ thuộc số dòng); sửa `scripts/`, compose, Makefile, `config.py`, `processing/` (file của người khác, ghi vào backlog); cấu hình topic qua env (YAGNI).

## Các bước

- [x] Spike EventStreams 30 phút → [ingestion-spike.md](../ingestion-spike.md)
- [x] Chạy lại CP0 trên Windows 11 (CP1)
- [x] Envelope dùng chung + sửa key khi `wiki: null`
- [x] Replay: `run_replay`, exit code 0/1/2/3, `close()` không che exit code, đọc file có BOM
- [x] Fixture LIVE mẫu đã pseudonymize, có test chặn lộ danh tính
- [x] README, lộ trình 4 tuần, checkpoint → REVIEW
- [ ] Trọng + Linh review PR

## Quyết định

- Chờ nhóm chốt, xem [Cần nhóm quyết định](../backlog.md#cần-nhóm-quyết-định): BL-THANH-01 (allowlist), BL-THANH-02 (DLQ), BL-THANH-03 (`collector_version`), BL-THANH-04 (at-least-once).
- Của module (đã chốt): replay giữ send đồng bộ và dừng ở lỗi đầu tiên; giữ nguyên CLI mà smoke dùng; xử lý surrogate lẻ bằng cách giữ dạng `\u`-escape thay vì loại bỏ; sample LIVE là pseudonymized (title, revision ID là dữ liệu public, không phải ẩn danh hoàn toàn).
- Việc còn treo của module: [BL-THANH-14 → BL-THANH-18](../backlog.md#thành).

## Nhật ký

- 2026-10-15 — spike, CP1, envelope, replay error handling, LIVE sample, docs. Mỗi task có một subagent review riêng, cuối cùng có thêm một lượt review toàn branch. Commit `2c2a98e` (envelope); phần còn lại nằm ở các commit tiếp theo trên branch (chưa push). Evidence CP1 của Thành nằm ở mục Kết quả để Trọng tổng hợp ([BL-THANH-13](../backlog.md#trọng)).

## Kết quả

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Unit/API/dashboard | `.venv\Scripts\python -m pytest -q -m "not integration and not spark"` | 114 passed, 9 deselected |
| Lint | `.venv\Scripts\ruff check .` | All checks passed |
| Spark | `docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q` | 16 passed |
| E2E smoke | PowerShell: `$env:PYTHONUTF8=1; .venv\Scripts\python scripts\smoke_test.py` | passed, `smoke-20261015105416-8a24c9e61d684134bebfcd007f2ff583` |
| Exit code chạy thật | `docker compose stop kafka` rồi `docker compose run --rm --no-deps replay`; `--speed 0`; `--file /nope.jsonl` | 3 / 2 / 2; chạy bình thường ra 0, publish 11 event |

CP1 (15/10/2026, Windows 11, Docker Desktop 29.8.1 linux/amd64, Compose v5.5.1, Python 3.12.7, chạy trên working copy tại `8c28d80` = origin/main): suite 84 passed; Spark 16 passed; smoke passed `smoke-20261015101531-44a25c0b3f45409c93f43a411fa0aebb` (Bronze 11 / invalid 2 / Silver 7 / Gold 2, AppTest pass); dev stack API window 00:00 trả enwiki 5/5/0/1/1, viwiki 1 new page. Hai lỗi chỉ gặp trên Windows: [BL-THANH-06](../backlog.md#trọng) và BL-THANH-11. Không chạy `make` được thì dùng lệnh tương đương ở bảng trên.
