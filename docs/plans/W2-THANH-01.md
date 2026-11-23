Trạng thái: REVIEW · Owner: Thành · Reviewer: Trọng, Linh · Liên quan: W2-THANH-01, BL-THANH-01–04, BL-THANH-16

## Mục tiêu

Collector LIVE đọc Wikimedia SSE, gửi Kafka theo contract và phục hồi kết nối trong cùng tiến trình; lộ trình tổng ở [thanh-ingestion-4-tuan](thanh-ingestion-4-tuan.md).

## Phạm vi / Không làm

Ingestion/replay, test và tài liệu module của Thành. Không lưu vị trí qua restart, không sửa Compose/shared config của Trọng; quyết định liên nhóm vẫn ở [backlog](../backlog.md#cần-nhóm-quyết-định).

## Các bước

- [x] Pha 1: baseline, parser SSE và test; subagent review.
- [x] Pha 2: collector, envelope, ACK/resume và test; subagent review.
- [x] Pha 3: reconnect, shutdown, counters, integration; subagent review.
- [x] Pha 4: regression, LIVE ≥20 phút, tài liệu/evidence; subagent review và bàn giao.

## Quyết định

- Resume chỉ trong cùng tiến trình; sau restart bắt đầu stream hiện tại. Không tuyên bố exactly-once.
- Giữ payload/key hiện tại; không lọc allowlist ở collector theo contract hiện có. Các quyết định BL-THANH-01–04 chưa đóng.
- Mỗi pha có review độc lập; không commit/push khi chưa được cho phép.

## Nhật ký

- 2026-11-23 — Bắt đầu triển khai W2 theo plan bốn pha; giữ thay đổi lộ trình có sẵn.
- 2026-11-23 — Pha 1: parser có 5 test pass sau review độc lập (BOM, ID reconnect); suite nhẹ 143 pass/2 lỗi Compose subprocess/5 skip/59 deselected, hai Compose config trực tiếp exit 0. Docker engine 29.8.1; Docker CLI không nhận plugin compose với môi trường rút gọn của test, nguyên nhân gốc chưa xác định.
- 2026-11-23 — Chẩn đoán baseline: môi trường test thiếu `PROGRAMFILES`; thêm riêng biến đó vào subprocess khiến `docker compose version` exit 0. Mở BL-THANH-38 cho Trọng theo ownership.
- 2026-11-23 — Review độc lập phần ACK phát hiện cursor có thể vượt future lỗi và `meta.dt` chưa kiểm validate trước log; thêm regression RED→GREEN, khóa tracker khi lỗi và chỉ lưu timestamp hợp lệ. Runtime tiếp tục ở pha 3.
- 2026-11-23 — Review pha 3 phát hiện close SSE có thể chặn, URL sai retry vô hạn, HTTP 408/429 và Kafka send có thể chặn lâu; thêm regression, đóng response bất đồng bộ, phân loại lỗi và giới hạn Kafka `max_block_ms=1000`. Còn kiểm chứng Kafka/LIVE thực tế.
- 2026-11-23 — Review pha 4 phát hiện lỗi ACK khi shutdown có thể bị che, thiếu log counters lúc reconnect và timeout Compose quá ngắn; thêm regression/sửa, mở BL-THANH-39 cho Trọng và hướng dẫn `stop -t 100`.
- 2026-11-23 — Chạy Kafka integration với SSE giả và broker project riêng: `$env:WIKIPULSE_TEST_KAFKA='127.0.0.1:29092'; .\.venv\Scripts\python.exe -m pytest ingestion/collector/tests/test_kafka_integration.py -q -p no:cacheprovider` → 1 passed. Test dùng topic UUID và tự xóa topic đó. Suite nhẹ sau workaround `DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'`: 161 passed, 5 skipped, 60 deselected; `ruff check .` pass.
- 2026-11-23 — Bổ sung regression ACK timeout không tăng `publish_failed` (RED→GREEN); build lại image trước lượt LIVE cuối. Cập nhật contract mô tả implementation và giới hạn, chờ Linh review consumer.
- 2026-11-23 — Review độc lập cuối không thấy thêm lỗi nghiêm trọng, đối chiếu hash image/source khớp; bàn giao REVIEW cho Trọng/Linh, chưa đóng quyết định nhóm.

## Kết quả

### Kiểm chứng ngày 23/11/2026

- `$env:DOCKER_CONFIG='C:\Program Files\Docker\Docker\resources'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -m 'not integration and not spark' --tb=short` → **164 passed, 5 skipped, 60 deselected**, 26 warnings dependency. Không đặt workaround thì 2 test Compose lỗi vì BL-THANH-38.
- `.\.venv\Scripts\ruff.exe check .` và `git diff --check` → exit 0.
- Test Kafka/SSE giả: lệnh trong Nhật ký → **1 passed** với Kafka broker riêng. Test network với broker thật, không chứng minh không mất dữ liệu ở mọi kịch bản outage.
- LIVE: Docker Compose project `wikipulse-thanh-w2-20261123`, Kafka host port 29092, `PIPELINE_MODE=LIVE`, build `docker compose -p wikipulse-thanh-w2-20261123 --profile live up -d --build collector`. Image `sha256:be7e1847e7c1ffd3ddc560b4163c0e9fb7fa8a25a42c680da59bb8189603be7a` từ working tree chưa commit trên base `0c59b03`. Collector chạy **05:07:02–05:27:47 UTC**, khoảng **20 phút 45 giây**, restart count 0. Ngắt mạng collector 75 giây rồi nối lại: counters từ 802 ACK lên 3.793 sau reconnect. Cuối lượt **received=40.112, published=40.112, reconnects=6, publish_failed=0, parse_errors=0**; `docker compose -p wikipulse-thanh-w2-20261123 --profile live stop -t 100 collector` → exit 0, container exit 0.
- Kafka `kafka-get-offsets.sh --bootstrap-server kafka:9092 --topic wikipedia.recentchange.raw` tăng từ `0:9204,1:8915,2:10090` ở giữa lượt lên `0:20975,1:19765,2:22170` trước khi dừng. Kafka volume chứa raw LIVE chỉ lưu tạm; đã dọn đúng project bằng `docker compose -p wikipulse-thanh-w2-20261123 --profile live down --volumes --remove-orphans` → exit 0. Không commit raw/log chứa thông tin nguồn.
- SHA-256 source trong working tree của lần build: `main.py` `a8ac27ba480836cbe9851546623f697d0a5e14c6754de7fc4dec5cbb34f01262`; `collector.py` `a51edc833924156e597809d88f16f402da2af0e38a844e1cd7c3970472659f12`; `sse.py` `9a5b254ccf1a7fc41f0215c19c3bfbdfa5b6564647dd17b302b28b682476b931`.

Các test trên không đóng CP2 toàn nhóm. Chờ Trọng/Linh review, đặc biệt thay đổi mô tả contract; BL-THANH-01–04 vẫn chờ nhóm quyết định. Resume chỉ trong cùng tiến trình.
