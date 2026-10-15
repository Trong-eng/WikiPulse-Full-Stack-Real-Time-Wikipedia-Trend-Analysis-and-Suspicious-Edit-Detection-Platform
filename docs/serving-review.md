# Review serving — W1-NHAN-01

Nhân tiếp quản CQL/sink/API ngày 15/10/2026. Ghi chú này là review khóa Cassandra và API schema của CP0, kèm việc chuyển sang tuần 2–3.

## Đã kiểm chứng

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Upsert absolute, retry không cộng đôi | Đúng trên Cassandra thật | `api/tests/test_cassandra_integration.py` |
| Latest window DESC, `LIMIT ?` bind, timestamp UTC round-trip | Đúng trên Cassandra 4.1.8 | như trên |
| Query window với offset khác UTC (+07:00) | Trả đúng window UTC | như trên |
| Schema init idempotent | Chạy lại không lỗi | như trên |
| CP0 trên Windows/x86_64 | enwiki 5/5/0/1/1, viwiki 1/0/1/0/0 khớp `expected_activity.json`; replay lần hai không đổi counts | `make up` + `make replay` + curl `/api/v1/activity` |

Chạy integration test với node Cassandra bất kỳ:

```bash
docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8
CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 .venv/bin/python -m pytest -q -m integration api/tests
docker rm -f wikipulse-it
```

Mỗi lần chạy dùng keyspace `wikipulse_it_<random>` và tự drop, không đụng dữ liệu dev.

## Thay đổi trong lần tiếp quản

- `ActivityRow` validate wiki identifier, `window_end > window_start`, `edit_count + new_page_count ≤ event_count`, `anonymous/bot_edit_count ≤ edit_count` (khớp `activity_windows` của Linh). Row sai làm batch fail, Spark retry từ checkpoint thay vì ghi số sai.
- `/api/v1/activity` công bố response 503 `DEPENDENCY_UNAVAILABLE` trong OpenAPI để Mạnh dựa vào schema.
- `pyasyncore` thêm vào dev deps cho Python 3.12: `cassandra-driver` 3.29.2 không có event loop khi thiếu `asyncore`/libev. Container Python 3.11 không bị ảnh hưởng.
- `.gitattributes` giữ LF cho `*.sh`: checkout Windows với `core.autocrlf=true` làm `init-topics` lỗi `set: pipefail: invalid option name`.

## Review khóa `wiki_activity_by_window`

- `PRIMARY KEY ((wiki), window_start)` DESC phục vụ đúng hai query của API (latest N, exact window) mà không cần `ALLOW FILTERING`.
- Kích thước partition: 1.440 row/ngày/wiki, ~525k row/năm. Ổn cho demo; tuần 3 cần TTL (`default_time_to_live`) hoặc bucket theo ngày `((wiki, day), window_start)` trước khi chạy LIVE dài ngày.
- Upsert dùng write timestamp của Cassandra (last-write-wins theo thời điểm ghi). An toàn vì Spark `foreachBatch` ghi batch tuần tự và chỉ replay batch chưa commit; không dùng `USING TIMESTAMP`.
- Ghi từng row đồng bộ qua `toLocalIterator`, đủ cho tải demo. Test capacity tuần 3 quyết định có cần `execute_concurrent` không.

## Đề xuất cho tuần 2 (cần chốt với Linh/Mạnh)

- Trends: bảng `page_trends_by_window`, khóa `((wiki, window_start), page_key)`; score là cột thường, top-N đọc cả partition rồi sort, cap 5.000 row, vượt cap trả lỗi rõ.
- Suspicious edits: `((wiki, window_start), event_id)`; risk reasons là `set<text>`; không có username/IP.
- Event detail: bảng tra cứu `events_by_id` với `PRIMARY KEY (event_id)`.
- Thống nhất envelope lỗi cho mọi endpoint (hiện 422 của FastAPI là list, 503 là object).
