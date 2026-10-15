# Backlog WikiPulse

Những việc **chưa có lịch**: quyết định chờ chốt, lỗi, nợ kỹ thuật, phát hiện cross-team, việc sau MVP. Việc đã có lịch nằm ở [checkpoints.md](checkpoints.md). Quy trình chung ở [AGENTS.md](../AGENTS.md).

## Cách ghi

Format, mỗi item 1–3 dòng:

`- **BL-<NGƯỜI TẠO>-NN** · <TRẠNG THÁI> · <loại> · <P1|P2|P3> · owner: <ai xử lý> — mô tả. Nguồn: <file:line/doc/PR> · Lịch: <ID checkpoint hoặc —>`

- **ID**: `NGƯỜI TẠO` là tên không dấu viết hoa (`TRONG`, `THANH`, `LINH`, `NHAN`, `MANH`). `NN` là số tiếp theo trong các ID **của chính bạn** (tra trong file này). Mỗi người tự đếm nên không bị trùng giữa các branch. Không đổi hay dùng lại ID cũ.
- **Trạng thái**: `PROPOSED` (người tạo giao cho người khác, chờ owner nhận) → `OPEN` → `IN_PROGRESS` → `DONE (PR #…)` hoặc `WONTFIX (lý do)`. Đổi trạng thái tại chỗ; không chuyển hay xóa item.
- **Loại**: `decision` · `bug` · `tech-debt` · `finding` · `later`. **Ưu tiên**: P1 chặn checkpoint gần nhất · P2 nên làm trong tuần · P3 khi rảnh.
- **Quyền**: ai cũng được thêm item và ghi chú (thêm dòng con `  - YYYY-MM-DD <tên>: …`). Owner của item đổi trạng thái và `Lịch:`; nhận item `PROPOSED` thì chuyển sang `OPEN`, không nhận thì `WONTFIX (lý do)`. Người tạo chỉ sửa mô tả khi item còn `PROPOSED`.
- **Item `decision`**: người duyệt ghi trong owner đóng item bằng `DONE (quyết định: …; ghi ở <contracts.md/plan>, PR #…)`. Nội dung đã chốt phải được ghi vào file đích; backlog chỉ giữ link.
- **Conflict**: rebase trước khi push và kiểm lại ID của mình. Nếu hai người cùng thêm item vào cuối một mục và bị conflict, giữ cả hai dòng.
- Đặt item vào mục của **người phải xử lý**. Chỉ owner ghi ID checkpoint vào `Lịch:`; người tạo muốn gợi ý thì viết `Lịch: đề xuất <ID>`.

## Cần nhóm quyết định

- **BL-THANH-01** · PROPOSED · decision · P1 · owner: cả nhóm (Linh duyệt) — Lọc `WIKI_ALLOWLIST` ở Silver (giữ contract hiện tại), collector không lọc. Toàn stream đo được 29 event/s, dưới trần Spark ~100/s. Nguồn: [ingestion-spike.md](ingestion-spike.md#lưu-lượng) · Lịch: W2-THANH-01
- **BL-THANH-02** · PROPOSED · decision · P1 · owner: Trọng + Linh + Thành — Kafka DLQ sink: Linh làm trong Spark, hay bỏ khỏi contract vì `bronze/invalid` đã là quarantine (bỏ thì phải sửa `create_topics.sh`, compose, README). Nguồn: `docs/contracts.md` mục Silver · Lịch: —
- **BL-THANH-03** · PROPOSED · decision · P2 · owner: Linh — `collector_version` = `replay-<COLLECTOR_VERSION>` / `live-<COLLECTOR_VERSION>`, mặc định vẫn `replay-0.1.0`. Nguồn: [replay/README.md](../replay/README.md#envelope) · Lịch: W2-THANH-01
- **BL-THANH-04** · PROPOSED · decision · P1 · owner: cả nhóm — Delivery at-least-once: Bronze có thể chứa bản trùng, Silver dedup trong 10 phút. Collector mất kết nối lâu hơn 10 phút rồi resume thì event cũ thành late, có thể bị loại khỏi Silver. Nguồn: [ingestion-spike.md](ingestion-spike.md#kết-nối) · Lịch: W2-THANH-01
- **BL-THANH-05** · PROPOSED · decision · P2 · owner: Linh + Nhân + Mạnh — Trên LIVE, `categorize` chiếm 36% event, nên `event_count` (mọi event hợp lệ) cao hơn `edit_count` nhiều. Cần chốt ý nghĩa metric và cách dashboard hiển thị. Nguồn: [ingestion-spike.md](ingestion-spike.md#lưu-lượng) · Lịch: —

## Trọng

- **BL-THANH-06** · PROPOSED · bug · P2 · owner: Trọng — Makefile không chạy được trên Windows: `install` gọi `python3`, `PYTHON ?= .venv/bin/python`, `.venv/bin/ruff`; Windows mặc định không có `make`. Nguồn: `Makefile:1,8,30` · Lịch: —
- **BL-THANH-07** · PROPOSED · tech-debt · P2 · owner: Trọng — Thêm `.gitattributes` `*.sh text eol=lf`, vì checkout có `autocrlf=true` sẽ làm hỏng script được mount vào container. Nhân đã có file này trên branch `nhan/w1-cassandra-api-takeover`. Nguồn: `scripts/create_topics.sh` · Lịch: —
- **BL-THANH-08** · PROPOSED · tech-debt · P2 · owner: Trọng — Đặt retention cho topic raw: LIVE khoảng 3,4 GB/ngày, mà retention mặc định của Kafka là 7 ngày. `docs/development.md` dự kiến xử lý retention ở tuần 3. Nguồn: [ingestion-spike.md](ingestion-spike.md#lưu-lượng), `scripts/create_topics.sh` · Lịch: đề xuất W3-TRONG-01
- **BL-THANH-09** · PROPOSED · tech-debt · P2 · owner: Trọng — Thêm `restart: on-failure` cho service `collector`, làm lưới an toàn cho yêu cầu LIVE ≥15 phút. Nguồn: `docker-compose.yml:133-142` · Lịch: đề xuất W2-TRONG-01
- **BL-THANH-10** · PROPOSED · bug · P3 · owner: Trọng — `COLLECTOR_VERSION` có trong `.env.example` nhưng không có trong `x-app-env`, nên container luôn dùng giá trị mặc định. Nguồn: `docker-compose.yml:3-13` · Lịch: —
- **BL-THANH-11** · PROPOSED · bug · P2 · owner: Trọng — `scripts/smoke_test.py:40` gọi `subprocess.run(text=True)` mà không đặt encoding. Trên Windows nó dùng cp1252: output bị mojibake và có lúc `stdout=None`, có thể làm smoke fail giả. Sửa: `encoding="utf-8", errors="replace"`; tạm thời chạy với `PYTHONUTF8=1`. Nguồn: [W1-THANH-01](plans/W1-THANH-01.md#kết-quả) · Lịch: —
- **BL-THANH-12** · PROPOSED · tech-debt · P3 · owner: Trọng — Thêm `CLAUDE.local.md` vào `.gitignore` (ghi chú cá nhân theo [AGENTS.md](../AGENTS.md)). Nguồn: `.gitignore` · Lịch: —
- **BL-THANH-13** · PROPOSED · tech-debt · P2 · owner: Trọng — Đồng bộ docs của Trọng với AGENTS.md:
- **BL-THANH-31** · PROPOSED · tech-debt · P3 · owner: Trọng — Đưa script kiểm docs (link tương đối + mọi `*.md` khớp bản đồ docs trong AGENTS.md) vào `scripts/` và chạy trong `make test`/CI. Bản tạm nằm trong [thanh-agents-backlog](plans/thanh-agents-backlog.md#kết-quả). Nguồn: AGENTS.md §4 · Lịch: —
  `docs/development.md` (branch `codex/<role>-<task>` → `<owner>/<ID>-<slug>`; thứ tự đọc thêm backlog + AGENTS.md); `docs/checkpoints.md` §Quy tắc (Evidence là link tới plan); `plans.md` (mục backlog sau MVP link sang file này); `docs/implementation-log.md` (dòng đầu "lịch sử CP0, việc mới ở docs/plans/"); `README.md` (link AGENTS/backlog; bảng ownership thêm `ingestion/envelope.py`, `tests/fixtures/`, `docs/plans/`); tổng hợp evidence CP1 của Thành từ [W1-THANH-01](plans/W1-THANH-01.md#kết-quả). Nguồn: [thanh-agents-backlog](plans/thanh-agents-backlog.md) · Lịch: —

## Thành

- **BL-THANH-14** · OPEN · tech-debt · P3 · owner: Thành — Một số lỗi đầu vào vẫn ra traceback và exit 1 thay vì exit 2 có log `replay_failed`: `--file` không phải UTF-8, `PIPELINE_MODE` sai, `REPLAY_SPEED_FACTOR` không phải số, `KafkaConfigurationError`. Nguồn: `replay/replay_producer.py` `main()` · Lịch: —
- **BL-THANH-15** · OPEN · tech-debt · P3 · owner: Thành — Chưa có test `caplog` cho các dòng `replay_failed`. Test flush lỗi chưa assert `closed`. Validation `--start -1` / `--end <= --start` chưa có test. Nguồn: `replay/tests/test_replay.py` · Lịch: —
- **BL-THANH-16** · OPEN · tech-debt · P2 · owner: Thành — `encode_event` trả `(None, raw)` cho mọi loại lỗi parse, nên counter `parse_errors` của collector không phân biệt được các loại. Nguồn: `ingestion/envelope.py` · Lịch: W2-THANH-01
- **BL-THANH-17** · OPEN · tech-debt · P3 · owner: Thành — Các edge case của envelope: `now` không có timezone ra ISO không offset; `page_id=""` ra key `enwiki:`; `COLLECTOR_VERSION=""` ra `replay-`; `ingestion/` chưa có `__init__.py`. Nguồn: `ingestion/envelope.py` · Lịch: —
- **BL-THANH-18** · OPEN · tech-debt · P3 · owner: Thành — `except Exception` trong `run_replay` bọc cả lỗi lập trình thành `send_error`; nên thu hẹp về `KafkaError`. Nguồn: `replay/replay_producer.py` `run_replay` · Lịch: —

## Linh

- **BL-THANH-19** · PROPOSED · finding · P1 · owner: Linh — LIVE không có field `anon` và không có user dạng IP. Editor ẩn danh là temporary account `~2026-NNNNN-NN` (11% event của enwiki+viwiki). `is_anonymous` hiện chỉ dựa vào `anon`/regex IP, nên `anonymous_edit_count` gần bằng 0 và ANONYMOUS_EDIT không bao giờ bắn. Nguồn: `processing/spark/wikipulse/transformations.py:161-166`, [ingestion-spike.md](ingestion-spike.md#shape-event-khác-fixture-cp0) · Lịch: đề xuất W2-LINH-01
- **BL-THANH-20** · PROPOSED · finding · P2 · owner: Linh — Canary thật chỉ có `{"$schema","meta"}`, nên rơi vào `bronze/invalid` với `MISSING_WIKI` (2 dòng mỗi lần phát). Filter `domain != canary` không bao giờ gặp canary thật, và canary trong fixture CP0 (có `wiki=enwiki`) không giống LIVE. Mẫu thật: `tests/fixtures/recentchange_live_sample.jsonl`. Nguồn: `processing/spark/wikipulse/transformations.py:101,139` · Lịch: đề xuất W2-LINH-01
- **BL-THANH-21** · PROPOSED · finding · P3 · owner: Linh — Event thiếu `user` đều nhận chung một `user_hash` = sha2(salt + `|` + ""); nên để null. Nguồn: `processing/spark/wikipulse/transformations.py:151-153` · Lịch: —

## Nhân

- **BL-THANH-22** · PROPOSED · tech-debt · P3 · owner: Nhân — Đề xuất theo AGENTS.md: khi merge, đổi `docs/serving-review.md` thành plan `docs/plans/W1-NHAN-01.md`. Nguồn: branch `nhan/w1-cassandra-api-takeover` · Lịch: —
- **BL-THANH-23** · PROPOSED · tech-debt · P3 · owner: Nhân — Đề xuất theo AGENTS.md: nháp `docs/contracts-w2-draft.md` sửa thẳng vào `docs/contracts.md` trên PR draft, không giữ file nháp riêng. Nguồn: branch `nhan/w2-serving-contract-draft` · Lịch: đề xuất W2-NHAN-01

## Mạnh

- **BL-THANH-24** · PROPOSED · finding · P2 · owner: Mạnh — Đồng hồ máy dev có thể chậm ít nhất ~10 s so với `meta.dt`. Kiểm `w32tm /query /status` (Windows) và đồng bộ NTP trước khi đo độ trễ provisional 30–60 s. Nguồn: [ingestion-spike.md](ingestion-spike.md#việc-cần-báo-các-owner-khác) · Lịch: đề xuất W3-MANH-01

## Sau MVP

Đây là danh sách thuộc mục backlog trong [plans.md](../plans.md), chưa ai nhận.

- **BL-THANH-25** · OPEN · later · P3 · owner: — — ML cho phát hiện chỉnh sửa đáng ngờ. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-26** · OPEN · later · P3 · owner: — — HA (nhiều broker/node, replication > 1). Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-27** · OPEN · later · P3 · owner: — — Cloud deployment (Kubernetes hiện mới là skeleton). Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-28** · OPEN · later · P3 · owner: — — Backfill dữ liệu lịch sử. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-29** · OPEN · later · P3 · owner: — — Benchmark chuyên sâu. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-30** · OPEN · later · P3 · owner: — — Risk rule cho burst/rapid edits. Nguồn: plans.md §2 · Lịch: —
