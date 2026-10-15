# Ingestion/Kafka/Replay — kế hoạch 4 tuần (Thành)

Trạng thái: ACTIVE · Owner: Thành · Reviewer: Trọng, Linh · Liên quan: W1–W4-THANH-01

Phạm vi: W1–W4-THANH-01 trong [checkpoints](../checkpoints.md). Kế hoạch này chi tiết hóa phần việc của Thành trong [plans.md](../../plans.md); nó không thay đổi contract. Mọi đổi contract vẫn qua PR có Linh (consumer) review. Kết quả spike EventStreams ở [ingestion-spike.md](../ingestion-spike.md).

## Quyết định xuyên suốt

Các quyết định cần cả nhóm chốt nằm ở [backlog](../backlog.md#cần-nhóm-quyết-định); bảng dưới chỉ ghi đề xuất và link tới item tương ứng.

| Chủ đề | Quyết định |
|---|---|
| Delivery | Đề xuất at-least-once, chờ chốt: [BL-THANH-04](../backlog.md#cần-nhóm-quyết-định). |
| Allowlist | Đề xuất collector không lọc (đo được 29 event/s), chờ chốt: [BL-THANH-01](../backlog.md#cần-nhóm-quyết-định). |
| Envelope | `ingestion/envelope.py` dùng chung cho replay và collector. `collector_version` = `replay-<ver>` / `live-<ver>`, mặc định `replay-0.1.0`. Format chờ Linh duyệt: BL-THANH-03. |
| CLI replay | Giữ nguyên flags mà smoke dùng; mode mới chỉ thêm flag, mặc định không đổi hành vi. |
| Exit code | 0 OK · 1 lỗi gửi/flush · 2 dùng sai · 3 không kết nối được broker. |
| Ownership | Không sửa Makefile/compose/`scripts/`/`config.py`/`processing/`; thay đổi ở đó ghi thành item trong [backlog](../backlog.md) cho owner. |

## Lộ trình

| Tuần | Mục tiêu | Deliverable / evidence | Phụ thuộc |
|---|---|---|---|
| W1 | Nền tảng: dữ liệu thật quyết định thiết kế, replay chắc chắn | Spike notes; CP0 pass trên Windows; replay xử lý lỗi + exit code; envelope chung; fixture LIVE mẫu đã ẩn danh; README | Trọng (issues), Linh (contract, sample) |
| W2 | LIVE MVP, xử lý rủi ro 15 phút sớm | SSE parser test bằng raw đã capture; User-Agent bắt buộc; `PIPELINE_MODE=LIVE`; counters log JSON mỗi 30 s; reconnect backoff + jitter + cap; resume `Last-Event-ID`; flush theo lô; SIGTERM flush. Evidence: log LIVE ≥20 phút có ≥1 reconnect + records trong Kafka | Trọng (`restart: on-failure`, retention), Linh (`meta.dt`, temp accounts, canary) |
| W3 | Độ bền và replay timing | Test Kafka outage (so số `meta.id` duy nhất, marker `integration`); `--timing original`; `--record` ghi JSONL ẩn danh làm dự phòng demo; regression fixture; đo thời gian Spark rút backlog | Linh (backlog), Trọng (HDFS) |
| W4 | Bàn giao, không thêm tính năng | Bugfix; runbook ingestion; LIVE 30 phút trên máy thứ hai; demo nguồn cùng Mạnh | Mạnh, cả nhóm (CP4) |

## Thiết kế collector W2

```
loop:
  connect SSE (User-Agent mô tả + link repo; Last-Event-ID = last_acked_id; read timeout ~60 s)
  for event in parse_sse(stream):           # bỏ comment ':', gộp data nhiều dòng, nhớ id
      producer.send(topic, key, encode_event(..., source="live"))
      pending_id = event.id
      mỗi N event hoặc 1 s: producer.flush() → last_acked_id = pending_id
  on lỗi (server đóng bất kỳ lúc nào / read timeout / KafkaError): đóng stream, backoff min(cap, base·2^n)+jitter, reconnect
  on SIGTERM: flush, log counters, exit 0
counters: received, published, publish_failed, parse_errors, reconnects, last_event_time (log mỗi 30 s)
```

Code: `ingestion/collector/app/{sse.py,collector.py,main.py}`, tests ở `ingestion/collector/tests/`. Cần thêm `requests` vào `replay/requirements.txt` vì collector dùng chung image replay.

## Rủi ro

| Rủi ro | Mitigation |
|---|---|
| Server đóng connection không theo chu kỳ (spike: sau 901 s và 683 s); CP4 cần LIVE ≥15 phút | Reconnect + `Last-Event-ID` nằm trong MVP W2 |
| Thiếu hoặc dùng UA mặc định → HTTP 403 (đã xác nhận) | UA mô tả bắt buộc, có test |
| Mất mạng lúc demo | `--record` (W3) → replay recording |
| Đầy đĩa (khoảng 39 KB/s ≈ 3,4 GB/ngày raw) | [BL-THANH-08](../backlog.md#trọng); runbook `down -v` |
| Ẩn danh LIVE là temporary account `~…`, không phải IP | [BL-THANH-19](../backlog.md#linh) |
| Đổi contract thiếu review | Mọi thay đổi `contracts.md` qua PR có Linh duyệt |
