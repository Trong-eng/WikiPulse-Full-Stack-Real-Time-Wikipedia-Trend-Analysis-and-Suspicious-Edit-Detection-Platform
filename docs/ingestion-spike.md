# Spike EventStreams — W1-THANH-01

Ngày 15/10/2026, khoảng 10:14–10:44 UTC (đồng hồ máy chậm ít nhất ~10 s, xem mục Shape event), Windows 11. Client `requests` 2.32.3, User-Agent mô tả có link repo, `Accept: text/event-stream`, read timeout 60 s. Khi bị đóng thì kết nối lại sau 1 s với `Last-Event-ID` là `id:` cuối cùng nhận được. Capture raw (84 MB, chứa username thật) chỉ lưu local, không commit. Mẫu đã pseudonymize nằm ở `tests/fixtures/recentchange_live_sample.jsonl`.

Endpoint: `https://stream.wikimedia.org/v2/stream/recentchange`.

## Kết nối

| Quan sát | Kết quả | Hệ quả cho collector W2 |
|---|---|---|
| Không có User-Agent, hoặc dùng UA mặc định `python-requests/…` (kiểm thủ công bằng `curl -A "" / -A "python-requests/2.32.3"`, 15/10/2026) | **HTTP 403** (HAProxy) | UA mô tả là bắt buộc; thiếu thì fail ngay, không retry vô hạn |
| Server đóng stream | 2 lần trong 30 phút: sau **901 s** và **683 s** (`ChunkedEncodingError: Response ended prematurely`) | Không có chu kỳ cố định; reconnect là luồng bình thường, không phải lỗi hiếm. CP4 (LIVE ≥15 phút) không đạt nếu thiếu reconnect |
| Resume bằng `Last-Event-ID` | 3 đoạn liên tiếp: **0 hổng, 0 trùng** trên cả eqiad (52.642 event, offset 6611578012 → 6611630653) và codfw (14 event) | At-least-once qua resume là đủ; chỉ cập nhật ID sau khi Kafka ack |
| Dòng `id:` | JSON array chứa vị trí của **cả hai** topic, ví dụ `[{"topic":"eqiad.mediawiki.recentchange","partition":0,"timestamp":…},{"topic":"codfw…","partition":0,"offset":-1}]` | Coi là chuỗi opaque, gửi lại nguyên văn (không tách riêng một topic) |
| Comment/heartbeat | Chỉ quan sát `:ok` (3 lần, 1 lần/kết nối); khoảng lặng dài nhất giữa các dòng 0,66 s. Không kết luận được server có keep-alive khi stream rỗi hay không | Read timeout ~60 s là dư để phát hiện stream treo ở lưu lượng ~29 event/s |

## Lưu lượng

- **29,3 event/s** toàn stream, khoảng 1.340 byte/event, tức ~39 KB/s ≈ **3,4 GB/ngày** nếu Bronze/Kafka giữ mọi wiki.
- Top wiki: commonswiki 40%, wikidatawiki 21%, enwiki 7,6% (**2,2/s**), viwiki **0,10/s**.
- Type: edit 56%, **categorize 36%**, log 5%, new 3%.
- Toàn stream vẫn dưới trần Spark ~100 event/s (`MAX_OFFSETS_PER_TRIGGER=1000`/10 s), nên **không cần lọc allowlist ở collector**.

## Shape event (khác fixture CP0)

- **Không có `page_id`** (0/52.656) → key Kafka thực tế là `wiki:title`.
- `meta.dt` có mili-giây: `2026-10-15T10:13:55.773Z`; `timestamp` là epoch giây.
- **Không có field `anon` và không có user dạng IP.** Editor ẩn danh là *temporary account* `~2026-NNNNN-NN`, chiếm 461/4.156 event enwiki+viwiki (11%).
- `categorize` không có `length`/`revision`; `log` có `log_type/log_action/log_params`; `new` có `length.old`/`revision.old` null.
- **Canary**: quan sát được 1 lần (10:15:00.000Z), mỗi datacenter (eqiad, codfw) phát 1 event với `meta.id` khác nhau. Event chỉ có `{"$schema","meta"}`, không có `wiki/type/title/timestamp`.
- 49 edit enwiki/viwiki có byte delta ≤ −1.000 trong 30 phút (44 enwiki, 5 viwiki; 7 trong số đó là bot), đủ dữ liệu cho LARGE_DELETION.
- Có event không có field `user` (2 edit ruwiki trong capture).
- Thời điểm nhận sớm hơn `meta.dt` khoảng 10,1 s, ổn định ở cả 3 đoạn (`meta.dt` − `timestamp` chỉ +1,2 s). Suy ra đồng hồ máy chậm **ít nhất** ~10 s (chưa trừ độ trễ mạng).

## Việc cần báo các owner khác

Đã ghi thành item trong [backlog](backlog.md); owner xử lý ở đó, file này chỉ giữ số liệu đo được:
[BL-THANH-19](backlog.md#linh) temporary account không được tính là anonymous · BL-THANH-20 canary vào `bronze/invalid` · BL-THANH-21 event thiếu `user` · [BL-THANH-05](backlog.md#cần-nhóm-quyết-định) ý nghĩa `event_count` khi categorize chiếm 36% · [BL-THANH-08](backlog.md#trọng) retention · [BL-THANH-24](backlog.md#mạnh) đồng hồ/NTP trước khi đo độ trễ.
