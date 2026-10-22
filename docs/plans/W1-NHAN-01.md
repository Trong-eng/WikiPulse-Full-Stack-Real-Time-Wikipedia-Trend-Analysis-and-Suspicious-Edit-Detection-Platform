# W1-NHAN-01 — Tiếp quản CQL/sink/API, review khóa và API schema

Trạng thái: REVIEW · Owner: Nhân · Reviewer: Trọng, Mạnh · Liên quan: [checkpoints](../checkpoints.md), BL-THANH-22, contract tuần 2 ở PR #3

## Mục tiêu

Nhân hiểu, kiểm thử và chịu trách nhiệm được đường ghi activity từ Spark sang Cassandra và API đọc lại. Khóa và API schema của CP0 được review trước khi mở rộng sang trends/suspicious ở tuần 2.

## Phạm vi / Không làm

- Làm: `storage/cassandra/`, `shared/wikipulse_core/serving.py`, `api/`, test trên Cassandra thật, contract/data dictionary phần serving.
- Không làm: logic Spark (Linh), dashboard (Mạnh), Compose/Makefile/scripts (Trọng). Hai sửa lỗi Windows chạm file chung (`.gitattributes`, dev deps) đã ghi trong PR #1 để Trọng review.

## Các bước

- [x] Kiểm `ActivityRow` trước khi ghi: wiki identifier, `window_end > window_start`, `edit_count + new_page_count ≤ event_count`, `anonymous/bot_edit_count ≤ edit_count`
- [x] OpenAPI của `/api/v1/activity` công bố 503 `DEPENDENCY_UNAVAILABLE`
- [x] Integration test trên Cassandra thật: upsert khi retry, latest DESC + `LIMIT ?`, UTC round-trip, window có offset, schema init idempotent
- [x] Sửa lỗi chỉ gặp trên Windows: LF cho `*.sh`, `pyasyncore` cho Python 3.12
- [x] Chạy lại CP0 trên Windows
- [x] Review khóa và API schema (mục Quyết định)
- [ ] Trọng + Mạnh review (PR #1 đã merge ngày 15/10/2026, chưa có review)

## Quyết định

Review khóa `wiki_activity_by_window`:

- `PRIMARY KEY ((wiki), window_start)` DESC phục vụ đúng hai query của API (latest N, exact window), không cần `ALLOW FILTERING`.
- Partition tăng 1.440 row/ngày/wiki, khoảng 525 nghìn row/năm. Đủ cho demo; tuần 3 cần TTL hoặc bucket theo ngày `((wiki, day), window_start)` trước khi chạy LIVE dài ngày.
- Upsert dùng write timestamp của Cassandra (last-write-wins). An toàn vì `foreachBatch` ghi tuần tự và chỉ replay batch chưa commit; không dùng `USING TIMESTAMP`.
- Ghi đồng bộ từng row qua `toLocalIterator`, đủ cho tải demo. Test capacity tuần 3 quyết định có cần `execute_concurrent` không.
- Row sai làm cả batch fail để Spark retry từ checkpoint, thay vì ghi số sai.

Thiết kế tuần 2 (trends, suspicious edits, event detail, định dạng lỗi) chuyển sang contract ở PR #3.

## Nhật ký

- 2026-10-15 — tiếp quản, validation `ActivityRow`, OpenAPI 503, integration test, sửa lỗi Windows, CP0 trên Windows — PR #1 (`e20a9d7`)
- 2026-10-22 — đổi `docs/serving-review.md` thành plan này theo AGENTS.md (BL-THANH-22); chạy lại test trên `main` `f422959`

## Kết quả

Chạy lại ngày 22/10/2026 trên `main` `f422959`, Windows 11 x86_64, Python 3.12, Docker 29.7.2:

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Unit/API/dashboard/replay | `.venv\Scripts\python -m pytest -q -m "not integration and not spark"` | 121 passed |
| Lint | `.venv\Scripts\python -m ruff check .` | All checks passed |
| Cassandra thật (cassandra:4.1.8) | xem dưới | 4 passed; cả `api/tests` 33 passed |

```bash
docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8
CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 .venv/bin/python -m pytest -q -m integration api/tests
docker rm -f wikipulse-it
```

Mỗi lần chạy dùng keyspace `wikipulse_it_<random>` và tự drop, không đụng dữ liệu dev. Nếu thư mục tạm mặc định của pytest không ghi được, thêm `--basetemp <thư mục ngắn>`.

CP0 trên Windows ngày 15/10/2026 (`make up` + `make replay`, đọc `/api/v1/activity`): enwiki 5/5/0/1/1, viwiki 1/0/1/0/0, khớp `tests/fixtures/expected_activity.json`; replay lần hai không đổi counts.
