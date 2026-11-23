# W4-NHAN-01 — Serving/API regression, OpenAPI, data dictionary, runbook

Trạng thái: REVIEW · Owner: Nhân · Reviewer: Trọng, Mạnh · Liên quan: [checkpoints](../checkpoints.md), [W2-NHAN-01](W2-NHAN-01.md), [W3-NHAN-01](W3-NHAN-01.md), CP3

## Mục tiêu

Bàn giao phần Cassandra/sink/API: có test chặn API và CQL lệch khỏi contract, OpenAPI công bố được, data dictionary đúng với lược đồ, runbook đủ để người khác vận hành và xử lý sự cố.

## Phạm vi / Không làm

- Làm: snapshot OpenAPI + test hồi quy; test so cột CQL với model của store và với data dictionary; mô tả tham số trong OpenAPI; runbook serving; chạy lại toàn bộ test và smoke.
- Không làm (tuần 4 không thêm tính năng): đổi payload, thêm endpoint, đổi mặc định sink (BL-NHAN-01, Trọng), trang dashboard (BL-NHAN-02, Mạnh).

## Các bước

- [x] Mô tả tham số và endpoint trong OpenAPI; snapshot `api/openapi.json`
- [x] Test hồi quy: OpenAPI khớp snapshot, đủ mã lỗi, cột CQL khớp model, data dictionary đủ bảng
- [x] Runbook trong `api/README.md` và `storage/cassandra/README.md`
- [x] Chạy lại test nhẹ, Cassandra thật, smoke; cập nhật báo cáo

## Quyết định

- Runbook đặt trong README của module (theo bản đồ docs ở AGENTS.md §4), không tạo file runbook riêng.
- Snapshot OpenAPI nằm trong `api/` (module của Nhân); đổi schema mà không cập nhật snapshot thì test fail, buộc PR đó sửa luôn contract.

## Nhật ký

- 2026-11-23 — mở việc sau khi PR #6 merge; OpenAPI snapshot, test hồi quy, runbook; chạy hồi quy đầy đủ và thử từng lệnh runbook trên stack thật; báo cáo — branch `nhan/w4-nhan-01-serving-regression`

## Kết quả

Môi trường: Windows 11, Python 3.12.10, Docker 29.9.2, `main` 5e46a2d + nhánh này.

- Test nhẹ: `python -m pytest -q -m "not integration and not spark"` → 183 passed, 5 skipped (bỏ 2 test `tests/test_deployment.py` lỗi Docker CLI trên máy này, đã ghi ở [W2-NHAN-01](W2-NHAN-01.md#kết-quả)); `api/tests` 72 passed, trong đó 4 test hồi quy mới ở `api/tests/test_regression.py`. `ruff check .` sạch.
- Test hồi quy bắt được lỗi thật khi viết: endpoint event detail chưa có mô tả trong OpenAPI, và chưa có snapshot; cả hai đã sửa.
- Cassandra 4.1.8 thật: `CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 python -m pytest -m integration api/tests` → 8 passed.
- Smoke mặc định: `PYTHONUTF8=1 python scripts/smoke_test.py` → `status: passed`, gồm check `trends/suspicious/event API contract v0.2`; stack tự dọn.
- Runbook: trên compose project riêng với `SPARK_ANALYTICS_SINK=cassandra`, các lệnh `curl` và `cqlsh`/`nodetool` trong `api/README.md` và `storage/cassandra/README.md` chạy đúng (3 cửa sổ mới nhất từ chỉ mục, 2 trang ở cửa sổ 00:00, `fixture-004` risk 30 còn TTL 604.761 s).
