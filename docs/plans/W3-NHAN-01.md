# W3-NHAN-01 — Retry/upsert, latest window/detail, capacity, TTL

Trạng thái: DONE · Owner: Nhân · Reviewer: Trọng, Mạnh · Liên quan: [checkpoints](../checkpoints.md), [W2-NHAN-01](W2-NHAN-01.md), [contracts.md mục Tuần 2](../contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02)

## Mục tiêu

Chứng minh trên Cassandra thật: retry không đếm trùng, "mới nhất" và chi tiết event đúng, cap 5.000 dòng hoạt động, và chốt TTL bằng số đo.

## Phạm vi / Không làm

- Làm: test retry/upsert, latest window, event detail, capacity trên fake và node thật; đo byte/dòng; chốt TTL `events_by_id`.
- Không làm: TTL cho activity/trends/suspicious (đọc theo cửa sổ gần nhất, dung lượng nhỏ); cụm nhiều node; tải LIVE dài hạn.

## Các bước

- [x] Retry ghi lại cùng khóa → 1 dòng, giá trị mới nhất (activity, trends, suspicious, events)
- [x] Latest window qua bảng chỉ mục; exact window với múi giờ khác UTC
- [x] Cap 5.000: đúng 5.000 vẫn đọc được, 5.001 → `CAPACITY_EXCEEDED` (API 503), không cắt bớt
- [x] Đo dung lượng và tốc độ ghi; chốt TTL 7 ngày cho `events_by_id`

## Quyết định

- TTL `events_by_id` = 7 ngày (`default_time_to_live = 604800`). Lịch sử đầy đủ vẫn ở Bronze/Silver; event cũ hơn trả 404.
- Không đặt TTL cho bảng trends/suspicious trong MVP: dữ liệu đọc theo cửa sổ gần nhất, ít dòng (chỉ edit có điểm > 0, hoặc trang có edit trong 5 phút).
- Cap đếm số dòng đọc thật (LIMIT 5.001), không ước lượng.

## Nhật ký

- 2026-11-23 — test retry/latest/detail/capacity trên fake + Cassandra thật; script đo dung lượng; chốt TTL — PR #6 (cùng PR với W2-NHAN-01 vì dùng chung test)
- 2026-11-23 — PR #6 được duyệt và merge vào `main` (5e46a2d); chuyển DONE — PR #6

## Kết quả

- Test: xem lệnh trong [W2-NHAN-01](W2-NHAN-01.md#kết-quả); các test của việc này nằm trong `api/tests/test_serving_store.py`, `api/tests/test_api.py` và `api/tests/test_cassandra_integration.py`.
- Đo dung lượng, Cassandra 4.1.8 một node, 20.000 event tổng hợp đúng schema v0.2:
  `PYTHONPATH=. python storage/cassandra/measure_capacity.py --host 127.0.0.1 --port 19042 --container wikipulse-it --rows 20000`

  | Bảng | Dòng | Byte trên đĩa | Byte/dòng | Ghi tuần tự |
  |---|---|---|---|---|
  | `events_by_id` | 20.000 | 2.890.920 | 144,5 | 78 dòng/s |
  | `page_trends_by_window` | 5.000 | 84.194 | 16,8 | 79 dòng/s |

  Đọc top-20 của partition 5.000 dòng mất 156 ms. Dữ liệu tổng hợp lặp nhiều nên nén tốt hơn thật; con số trends chỉ dùng để thấy partition cap nhỏ.
- Ước tính TTL: allowlist enwiki 2,2 + viwiki 0,10 event/s ([ingestion-spike](../thanh/ingestion-spike.md)) ≈ 200.000 event/ngày × 145 byte ≈ 29 MB/ngày, ≈ 200 MB khi đầy 7 ngày. Tốc độ ghi 78 dòng/s lớn hơn ~34 lần lưu lượng allowlist và vẫn cao hơn cả stream toàn cục 29,3 event/s.
