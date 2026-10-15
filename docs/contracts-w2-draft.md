# Bản nháp contract tuần 2 — trends, suspicious edits, event detail

Trạng thái: **NHÁP** để Nhân trao đổi với Linh (đầu ra Spark) và Mạnh (API cho dashboard). Khi chốt, nội dung chuyển vào `docs/contracts.md` và file này bị xóa. Ngày soạn: 15/10/2026.

Ràng buộc kế thừa từ `plans.md` và contract v0.1: trends cửa sổ 5 phút trượt 1 phút; risk MVP gồm `LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`; chuẩn hóa trend bằng caps trong `config/scoring.yaml`, không dùng min/max của microbatch; upsert tổng tuyệt đối theo khóa ổn định; score không nằm trong khóa; không `ALLOW FILTERING`; top-N đọc đủ partition rồi sort, cap 5.000 dòng, vượt cap báo lỗi rõ; `limit` tối đa 100; không lộ username/IP.

Chỗ đánh dấu **[Linh quyết]** / **[Mạnh quyết]** là đề xuất của Nhân, chờ bên kia đồng ý.

## 1. Trends

### Đầu ra Spark (Linh → Nhân) [Linh quyết]

Một dòng cho mỗi `(wiki, window_start, page_key)`, cửa sổ 5 phút trượt 1 phút theo event time, watermark 10 phút, chế độ Update qua `foreachBatch` như activity.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| wiki | string | |
| window_start, window_end | timestamp UTC | window_end = window_start + 5 phút |
| page_key | string | `page_id` dạng chuỗi; thiếu thì `title:<page_title>`, để khóa luôn có giá trị |
| page_title | string | |
| namespace | int nullable | |
| edit_count | long | số `type=edit` |
| unique_editors | long | `approx_count_distinct(user_hash)`; streaming không hỗ trợ đếm phân biệt chính xác |
| abs_byte_delta | long | tổng `|byte_delta|`, bỏ qua null |
| trend_score | double 0–1 | Σ weight × min(giá trị / cap, 1) theo `config/scoring.yaml` |
| updated_at | timestamp UTC | |

Câu hỏi cho Linh: tính `trend_score` trong Spark (đề xuất, để Gold và Cassandra cùng một con số) hay để API tính?

### Cassandra (Nhân)

```sql
CREATE TABLE page_trends_by_window (
    wiki text, window_start timestamp, page_key text,
    window_end timestamp, page_title text, namespace int,
    edit_count bigint, unique_editors bigint, abs_byte_delta bigint,
    trend_score double, updated_at timestamp,
    PRIMARY KEY ((wiki, window_start), page_key)
);

-- Chỉ mục cửa sổ có dữ liệu, để tìm "cửa sổ mới nhất" mà không quét bảng.
CREATE TABLE trend_windows_by_wiki (
    wiki text, window_start timestamp, updated_at timestamp,
    PRIMARY KEY ((wiki), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
```

- Một partition = một wiki + một cửa sổ, nên top-N đọc đúng một partition. Ước tính enwiki LIVE: 100–200 edit/phút → dưới 1.000 trang/5 phút, dưới cap 5.000.
- Sink ghi `page_trends_by_window` trước, rồi upsert `trend_windows_by_wiki`; retry ghi lại cùng giá trị.
- Lưu ý cho dashboard: cửa sổ mới nhất luôn chưa đủ 5 phút dữ liệu và còn tăng.

### API (Nhân → Mạnh) [Mạnh quyết]

`GET /api/v1/trends?wiki=enwiki&window=<ISO có múi giờ, tùy chọn>&limit=20`

- Thiếu `window` → cửa sổ mới nhất trong `trend_windows_by_wiki`.
- API đọc cả partition, sort `trend_score` giảm dần, hòa thì `edit_count` giảm dần rồi `page_key` tăng dần (thứ tự ổn định giữa các lần gọi), trả `limit` dòng đầu.
- Envelope: `{data: TrendRow[], window_start, window_end, generated_at, source: "cassandra", pipeline_mode, provisional: true}`. Không có dữ liệu → 200, `data: []`, `window_start: null`.

## 2. Suspicious edits

### Đầu ra Spark [Linh quyết]

Một dòng cho mỗi sự kiện edit có `risk_score > 0`. Bucket theo phút của event time để khóa partition ổn định.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| wiki, event_id | string | |
| bucket_start | timestamp UTC | `date_trunc('minute', event_time)` |
| event_time | timestamp UTC | |
| page_key, page_title | string | |
| revision_new | long nullable | |
| byte_delta | long nullable | |
| is_anonymous, is_bot | boolean | |
| risk_score | int 0–100 | Σ weight của các lý do, chặn ở `max_score` |
| risk_reasons | array<string> | tập con của 3 mã MVP |
| updated_at | timestamp UTC | |

Câu hỏi cho Linh:
1. `REVERT_PATTERN` phát hiện bằng gì? Silver hiện không giữ comment/tag (quy tắc riêng tư). Phương án: (a) thêm cờ boolean `is_revert` vào Silver, suy ra từ comment/tag ở bước chuẩn hóa, không lưu text; (b) stateful theo page (A→B rồi B→A trong watermark). Nhân nghiêng về (a) vì đơn giản và không thêm toán tử có trạng thái.
2. Bot edit có bị loại khỏi danh sách không? Đề xuất: giữ nhưng không cộng điểm `ANONYMOUS_EDIT`; dashboard có filter.

### Cassandra (Nhân)

```sql
CREATE TABLE suspicious_edits_by_bucket (
    wiki text, bucket_start timestamp, event_id text,
    event_time timestamp, page_key text, page_title text,
    revision_new bigint, byte_delta bigint, is_anonymous boolean, is_bot boolean,
    risk_score int, risk_reasons set<text>, updated_at timestamp,
    PRIMARY KEY ((wiki, bucket_start), event_id)
);

CREATE TABLE suspicious_buckets_by_wiki (
    wiki text, bucket_start timestamp, updated_at timestamp,
    PRIMARY KEY ((wiki), bucket_start)
) WITH CLUSTERING ORDER BY (bucket_start DESC);
```

### API [Mạnh quyết]

`GET /api/v1/suspicious-edits?wiki=enwiki&window=<tùy chọn>&minutes=5&min_score=0&limit=20`

- Đọc `minutes` bucket gần nhất (mặc định 5, tối đa 15) kể từ `window` hoặc bucket mới nhất; mỗi bucket là một partition, tổng số dòng đọc vẫn tính vào cap 5.000.
- Sort `risk_score` giảm dần, rồi `event_time` giảm dần.
- Không trả `user_hash`: mã băm vẫn cho phép nối các chỉnh sửa của cùng một người qua thời gian, mà dashboard không cần điều đó.
- Mọi phản hồi kèm câu cố định: "Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."

## 3. Event detail

### Đầu ra Spark [Linh quyết]

Ghi mọi sự kiện Silver (append, `foreachBatch`) kèm `risk_score`, `risk_reasons` nếu có. Không có raw user, IP, comment.

### Cassandra (Nhân)

```sql
CREATE TABLE events_by_id (
    event_id text PRIMARY KEY,
    wiki text, event_time timestamp, page_key text, page_title text, namespace int,
    event_type text, revision_old bigint, revision_new bigint,
    length_old bigint, length_new bigint, byte_delta bigint,
    is_anonymous boolean, is_bot boolean, is_minor boolean,
    risk_score int, risk_reasons set<text>, pipeline_version text, processed_at timestamp
);
```

TTL đề xuất 7 ngày (chốt ở W3-NHAN-01 sau khi đo dung lượng).

### API

`GET /api/v1/events/{event_id}` → 200 `{data: EventDetail, generated_at, source, pipeline_mode}`; không có → 404 `EVENT_NOT_FOUND`.

## 4. Định dạng lỗi thống nhất [Mạnh quyết]

Giữ wrapper `detail` của FastAPI để không phá response 503 hiện có:

```json
{"detail": {"code": "INVALID_QUERY", "message": "wiki must be in WIKI_ALLOWLIST"}}
```

| HTTP | code | Khi nào |
|---|---|---|
| 422 | `INVALID_QUERY` | Tham số sai; với lỗi validate của FastAPI thêm `fields` |
| 404 | `EVENT_NOT_FOUND` | Không có event_id |
| 503 | `DEPENDENCY_UNAVAILABLE` | Cassandra lỗi (đã có) |
| 503 | `CAPACITY_EXCEEDED` | Partition vượt cap 5.000 dòng; không cắt bớt ranking |
| 501 | `NOT_IMPLEMENTED` | Endpoint chưa làm (đã có) |

## 5. Việc tiếp theo sau khi chốt

- Linh: viết output DataFrame + golden fixture cho trends/risk (W2-LINH-01).
- Nhân: CQL, sink idempotent, 3 endpoint, test trên fake và Cassandra thật (W2-NHAN-01).
- Mạnh: Trending/Suspicious dùng envelope trên (W2-MANH-01).
- Cập nhật `docs/contracts.md`, data dictionary và các mục tương ứng trong báo cáo kỹ thuật.
