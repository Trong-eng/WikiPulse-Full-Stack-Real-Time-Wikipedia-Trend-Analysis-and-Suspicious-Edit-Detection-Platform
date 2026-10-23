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

- **BL-THANH-01** · PROPOSED · decision · P1 · owner: cả nhóm (Linh duyệt) — Lọc `WIKI_ALLOWLIST` ở Silver (giữ contract hiện tại), collector không lọc. Toàn stream đo được 29 event/s, dưới trần Spark ~100/s. Nguồn: [ingestion-spike.md](thanh/ingestion-spike.md#lưu-lượng) · Lịch: W2-THANH-01
- **BL-THANH-02** · PROPOSED · decision · P1 · owner: Trọng + Linh + Thành — Kafka DLQ sink: Linh làm trong Spark, hay bỏ khỏi contract vì `bronze/invalid` đã là quarantine (bỏ thì phải sửa `create_topics.sh`, compose, README). Nguồn: `docs/contracts.md` mục Silver · Lịch: —
- **BL-THANH-03** · PROPOSED · decision · P2 · owner: Linh — `collector_version` = `replay-<COLLECTOR_VERSION>` / `live-<COLLECTOR_VERSION>`, mặc định vẫn `replay-0.1.0`. Nguồn: [replay/README.md](../replay/README.md#envelope) · Lịch: W2-THANH-01
- **BL-THANH-04** · PROPOSED · decision · P1 · owner: cả nhóm — Delivery at-least-once: Bronze có thể chứa bản trùng, Silver dedup trong 10 phút. Collector mất kết nối lâu hơn 10 phút rồi resume thì event cũ thành late, có thể bị loại khỏi Silver. Nguồn: [ingestion-spike.md](thanh/ingestion-spike.md#kết-nối) · Lịch: W2-THANH-01
- **BL-THANH-05** · PROPOSED · decision · P2 · owner: Linh + Nhân + Mạnh — Trên LIVE, `categorize` chiếm 36% event, nên `event_count` (mọi event hợp lệ) cao hơn `edit_count` nhiều. Cần chốt ý nghĩa metric và cách dashboard hiển thị. Nguồn: [ingestion-spike.md](thanh/ingestion-spike.md#lưu-lượng) · Lịch: —

## Trọng

- **BL-THANH-06** · PROPOSED · bug · P2 · owner: Trọng — Makefile không chạy được trên Windows: `install` gọi `python3`, `PYTHON ?= .venv/bin/python`, `.venv/bin/ruff`; Windows mặc định không có `make`. Nguồn: `Makefile:1,8,30` · Lịch: —
  - 2026-10-23 Thành: đã viết `scripts/wikipulse.ps1` (UTF-8 có BOM để PowerShell 5.1 đọc đúng comment tiếng Việt) với các target tương ứng `Makefile` (`help`, `install`, `build`, `up`, `init`, `replay`, `down`, `logs`, `config`, `test`, `test-spark`, `lint`, `smoke`). Script không tạo `.venv`, chỉ chạy khi `.venv` đã có ở root; `smoke` tự đặt `PYTHONUTF8=1` (BL-THANH-11). Đã chạy thử mọi target trên Windows 11, `smoke` passed; `Makefile` giữ nguyên. Lệnh gốc từng bước ở [tong-ket-1.md](../tong-ket-1.md#4-cách-chạy-lại-kết-quả-tuần-1-windows). Trọng duyệt: giữ thì thêm vào README/development.md và đóng item, không đồng ý thì xóa file.
- **BL-THANH-07** · PROPOSED · tech-debt · P2 · owner: Trọng — Thêm `.gitattributes` `*.sh text eol=lf`, vì checkout có `autocrlf=true` sẽ làm hỏng script được mount vào container. Nhân đã có file này trên branch `nhan/w1-cassandra-api-takeover`. Nguồn: `scripts/create_topics.sh` · Lịch: —
  - 2026-10-16 Thành: `.gitattributes` (`*.sh text eol=lf`) đã lên `main` qua PR #1 của Nhân; Trọng xác nhận rồi đóng item.
- **BL-THANH-08** · PROPOSED · tech-debt · P2 · owner: Trọng — Đặt retention cho topic raw: LIVE khoảng 3,4 GB/ngày, mà retention mặc định của Kafka là 7 ngày. `docs/development.md` dự kiến xử lý retention ở tuần 3. Nguồn: [ingestion-spike.md](thanh/ingestion-spike.md#lưu-lượng), `scripts/create_topics.sh` · Lịch: đề xuất W3-TRONG-01
- **BL-THANH-09** · PROPOSED · tech-debt · P2 · owner: Trọng — Thêm `restart: on-failure` cho service `collector`, làm lưới an toàn cho yêu cầu LIVE ≥15 phút. Nguồn: `docker-compose.yml:133-142` · Lịch: đề xuất W2-TRONG-01
- **BL-THANH-10** · PROPOSED · bug · P3 · owner: Trọng — `COLLECTOR_VERSION` có trong `.env.example` nhưng không có trong `x-app-env`, nên container luôn dùng giá trị mặc định. Nguồn: `docker-compose.yml:3-13` · Lịch: —
- **BL-THANH-11** · PROPOSED · bug · P2 · owner: Trọng — `scripts/smoke_test.py:40` gọi `subprocess.run(text=True)` mà không đặt encoding. Trên Windows nó dùng cp1252: output bị mojibake và có lúc `stdout=None`, có thể làm smoke fail giả. Sửa: `encoding="utf-8", errors="replace"`; tạm thời chạy với `PYTHONUTF8=1`. Nguồn: [W1-THANH-01](plans/W1-THANH-01.md#kết-quả) · Lịch: —
- **BL-THANH-12** · PROPOSED · tech-debt · P3 · owner: Trọng — Thêm `CLAUDE.local.md` vào `.gitignore` (ghi chú cá nhân theo [AGENTS.md](../AGENTS.md)). Nguồn: `.gitignore` · Lịch: —
- **BL-THANH-13** · PROPOSED · tech-debt · P2 · owner: Trọng — Đồng bộ docs của Trọng với AGENTS.md:
  `docs/development.md` (branch `codex/<role>-<task>` → `<owner>/<ID>-<slug>`; thứ tự đọc thêm backlog + AGENTS.md); `docs/checkpoints.md` §Quy tắc (Evidence là link tới plan); `plans.md` (mục backlog sau MVP link sang file này); `docs/trong/implementation-log.md` (dòng đầu "lịch sử CP0, việc mới ở docs/plans/"); `README.md` (link AGENTS/backlog; bảng ownership thêm `ingestion/envelope.py`, `tests/fixtures/`, `docs/plans/`, và `docs/<owner>/` thuộc từng người); tổng hợp evidence CP1 của Thành từ [W1-THANH-01](plans/W1-THANH-01.md#kết-quả). Nguồn: [thanh-agents-backlog](plans/thanh-agents-backlog.md) · Lịch: —
- **BL-THANH-31** · PROPOSED · tech-debt · P3 · owner: Trọng — Đưa script kiểm docs (link tương đối + mọi `*.md` khớp bản đồ docs trong AGENTS.md) vào `scripts/` và chạy trong `make test`/CI. Bản tạm nằm trong [thanh-agents-backlog](plans/thanh-agents-backlog.md#kết-quả). Nguồn: AGENTS.md §4 · Lịch: —
- **BL-THANH-32** · PROPOSED · decision · P3 · owner: Trọng — AGENTS.md §4 thêm folder docs theo người `docs/<owner>/`. Trọng quyết `docs/verification.md` và `docs/implementation-log.md` (lịch sử CP0 do Trọng viết) ở lại gốc `docs/` như tài liệu chung hay chuyển vào `docs/trong/`; nếu chuyển thì trong cùng PR sửa link, dòng bảng §4 của AGENTS.md và pattern của script kiểm docs. Nguồn: [thanh-agents-backlog](plans/thanh-agents-backlog.md#quyết-định) · Lịch: —
  - 2026-10-16 Thành: đã chuyển cả hai file vào `docs/trong/` theo yêu cầu của Thành, sửa tham chiếu trong `docs/checkpoints.md` (CP0, W1-TRONG-05), AGENTS.md §4 và script kiểm docs. `docs/development.md` giữ ở gốc vì là hướng dẫn setup/branch chung. Thay đổi được push thẳng lên `main` theo yêu cầu của Thành, không qua PR: Trọng xem commit, giữ thì đóng item, không đồng ý thì revert.
- **BL-THANH-33** · PROPOSED · decision · P2 · owner: Trọng — AGENTS.md §4 thêm dòng bản đồ docs cho `tong-ket-<N>.md` (tổng kết tuần gửi cấp trên, ở root, đóng băng sau khi gửi). Thành thêm theo yêu cầu của Thành khi viết `tong-ket-1.md`; Trọng duyệt giữ, đổi chỗ (vd. `docs/tong-ket/`) hoặc revert. Nguồn: [tong-ket-1.md](../tong-ket-1.md) · Lịch: —
- **BL-THANH-34** · PROPOSED · finding · P1 · owner: Trọng — CP1 chưa đóng: 4 việc W1 (THANH, LINH, NHAN, MANH) đều REVIEW mà chưa có review. Ngày 23/10 bốn nhánh `nhan/w1-nhan-01-plan`, `nhan/w2-serving-contract-draft` (PR #3 còn draft), `manh/w1-manh-01-dashboard-takeover`, `linh_tuan_1` được gộp thẳng vào `main` theo yêu cầu của Thành, không qua PR. Cần review chéo sau merge và tổng hợp evidence máy thứ hai. Nguồn: `docs/checkpoints.md` (CP1), [tong-ket-1.md](../tong-ket-1.md) · Lịch: —

## Thành

- **BL-THANH-14** · OPEN · tech-debt · P3 · owner: Thành — Một số lỗi đầu vào vẫn ra traceback và exit 1 thay vì exit 2 có log `replay_failed`: `--file` không phải UTF-8, `PIPELINE_MODE` sai, `REPLAY_SPEED_FACTOR` không phải số, `KafkaConfigurationError`. Nguồn: `replay/replay_producer.py` `main()` · Lịch: —
- **BL-THANH-15** · OPEN · tech-debt · P3 · owner: Thành — Chưa có test `caplog` cho các dòng `replay_failed`. Test flush lỗi chưa assert `closed`. Validation `--start -1` / `--end <= --start` chưa có test. Nguồn: `replay/tests/test_replay.py` · Lịch: —
- **BL-THANH-16** · OPEN · tech-debt · P2 · owner: Thành — `encode_event` trả `(None, raw)` cho mọi loại lỗi parse, nên counter `parse_errors` của collector không phân biệt được các loại. Nguồn: `ingestion/envelope.py` · Lịch: W2-THANH-01
- **BL-THANH-17** · OPEN · tech-debt · P3 · owner: Thành — Các edge case của envelope: `now` không có timezone ra ISO không offset; `page_id=""` ra key `enwiki:`; `COLLECTOR_VERSION=""` ra `replay-`; `ingestion/` chưa có `__init__.py`. Nguồn: `ingestion/envelope.py` · Lịch: —
- **BL-THANH-18** · OPEN · tech-debt · P3 · owner: Thành — `except Exception` trong `run_replay` bọc cả lỗi lập trình thành `send_error`; nên thu hẹp về `KafkaError`. Nguồn: `replay/replay_producer.py` `run_replay` · Lịch: —
- **BL-THANH-35** · DONE (commit `541cf9b`, kiểm ngày 23/10) · tech-debt · P1 · owner: Thành — Sau khi gộp 4 nhánh ngày 23/10 mới chạy lại unit test (121 passed), ruff và `docker compose config`; chưa chạy lại test Spark vì Docker Desktop tắt (thử bật lại báo "Docker Desktop is unable to start"). Số Spark trong `tong-ket-1.md` lấy từ lần chạy ngày 20/10 của Linh. Chạy `docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q` trước khi push. Nguồn: `processing/README.md` · Lịch: —
  - 2026-10-23 Thành: Docker đã chạy. Spark 26 passed; Cassandra thật (cassandra:4.1.8, container tạm `wikipulse-it` theo [W1-NHAN-01](plans/W1-NHAN-01.md#kết-quả)) 4 passed, `api/tests` 33 passed; unit 121 passed. Venv cũ thiếu `pyasyncore==1.0.4` (dependency Nhân thêm ở PR #1) nên lần đầu lỗi `DependencyException`; cài lại theo `pyproject.toml` là chạy được. `tong-ket-1.md` đã sửa câu số liệu.

## Linh

- **BL-THANH-19** · OPEN · finding · P1 · owner: Linh — LIVE không có field `anon` và không có user dạng IP. Editor ẩn danh là temporary account `~2026-NNNNN-NN` (11% event của enwiki+viwiki). `is_anonymous` hiện chỉ dựa vào `anon`/regex IP, nên `anonymous_edit_count` gần bằng 0 và ANONYMOUS_EDIT không bao giờ bắn. Nguồn: `processing/spark/wikipulse/transformations.py:161-166`, [ingestion-spike.md](thanh/ingestion-spike.md#shape-event-khác-fixture-cp0) · Lịch: W2-LINH-01
  - 2026-10-20 Linh: đã nhận và tái hiện bằng Spark trên fixture LIVE; evidence tại [W1-LINH-01](plans/W1-LINH-01.md#sample-live). Chưa sửa định nghĩa anonymous trong tuần 1.
- **BL-THANH-20** · OPEN · finding · P2 · owner: Linh — Canary thật chỉ có `{"$schema","meta"}`, nên rơi vào `bronze/invalid` với `MISSING_WIKI` (2 dòng mỗi lần phát). Filter `domain != canary` không bao giờ gặp canary thật, và canary trong fixture CP0 (có `wiki=enwiki`) không giống LIVE. Mẫu thật: `tests/fixtures/recentchange_live_sample.jsonl`. Nguồn: `processing/spark/wikipulse/transformations.py:101,139` · Lịch: W2-LINH-01
  - 2026-10-20 Linh: đã nhận và tái hiện bằng Spark; canary không vào Silver/activity. Evidence tại [W1-LINH-01](plans/W1-LINH-01.md#sample-live); cần review cách phân loại canary/quarantine trước khi thay đổi.
- **BL-THANH-21** · OPEN · finding · P3 · owner: Linh — Event thiếu `user` đều nhận chung một `user_hash` = sha2(salt + `|` + ""); nên để null. Nguồn: `processing/spark/wikipulse/transformations.py:151-153` · Lịch: —
  - 2026-10-20 Linh: đã nhận và tái hiện bằng hai event tổng hợp (thiếu user và user=null), vì fixture LIVE không có ca này. Evidence tại [W1-LINH-01](plans/W1-LINH-01.md#sample-live); giữ OPEN để review nullable semantics với consumer.
- **BL-THANH-36** · PROPOSED · tech-debt · P3 · owner: Linh — Branch `linh_tuan_1` và commit message `linh_commit` chưa theo AGENTS.md §6 (`<owner>/<ID>-<slug>`, message mô tả việc). Lần sau dùng ví dụ `linh/w2-linh-01-windows`. Nguồn: commit `7463171` · Lịch: —

## Nhân

- **BL-THANH-22** · DONE (PR #5) · tech-debt · P3 · owner: Nhân — Đề xuất theo AGENTS.md: khi merge, đổi `docs/serving-review.md` thành plan `docs/plans/W1-NHAN-01.md`. Phần ghi chú thiết kế thì đặt ở `docs/nhan/`; review và nhật ký vẫn vào plan. Nguồn: branch `nhan/w1-cassandra-api-takeover` · Lịch: —
  - 2026-10-16 Thành: PR #1 đã merge, `docs/serving-review.md` đang ở `main` và nằm ngoài bản đồ docs của AGENTS.md §4.
  - 2026-10-22 Nhân: chuyển toàn bộ nội dung vào [W1-NHAN-01](plans/W1-NHAN-01.md), xóa `docs/serving-review.md`; checkpoint link tới plan. Không cần `docs/nhan/` vì phần thiết kế tuần 2 đã nằm trong contract (PR #3).
- **BL-THANH-23** · DONE (PR #3) · tech-debt · P3 · owner: Nhân — Đề xuất theo AGENTS.md: nháp `docs/contracts-w2-draft.md` sửa thẳng vào `docs/contracts.md` trên PR draft, không giữ file nháp riêng. Nguồn: branch `nhan/w2-serving-contract-draft` · Lịch: W2-NHAN-01
  - 2026-10-22 Nhân: nội dung đã gộp vào mục Tuần 2 của [contracts.md](contracts.md), file nháp đã xóa; plan ở [W2-NHAN-01](plans/W2-NHAN-01.md).

## Mạnh

- **BL-THANH-24** · PROPOSED · finding · P2 · owner: Mạnh — Đồng hồ máy dev có thể chậm ít nhất ~10 s so với `meta.dt`. Kiểm `w32tm /query /status` (Windows) và đồng bộ NTP trước khi đo độ trễ provisional 30–60 s. Nguồn: [ingestion-spike.md](thanh/ingestion-spike.md#việc-cần-báo-các-owner-khác) · Lịch: đề xuất W3-MANH-01
- **BL-THANH-37** · PROPOSED · tech-debt · P2 · owner: Mạnh — 4 ảnh W1 trong `docs/bao-cao-ky-thuat/hinh/W1-Mạnh/` chưa đưa vào `main.tex` (còn `\dukiensua` ở `main.tex:1024`), thiếu ảnh trang Suspicious Edits; lệnh `AppTest` trong plan bị lược nên khó tái hiện; chưa có plan `W2-MANH-01`. Nguồn: [W1-MANH-01](plans/W1-MANH-01.md), `docs/bao-cao-ky-thuat/README.md` · Lịch: đề xuất W2-MANH-01

## Sau MVP

Đây là danh sách thuộc mục backlog trong [plans.md](../plans.md), chưa ai nhận.

- **BL-THANH-25** · OPEN · later · P3 · owner: — — ML cho phát hiện chỉnh sửa đáng ngờ. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-26** · OPEN · later · P3 · owner: — — HA (nhiều broker/node, replication > 1). Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-27** · OPEN · later · P3 · owner: — — Cloud deployment (Kubernetes hiện mới là skeleton). Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-28** · OPEN · later · P3 · owner: — — Backfill dữ liệu lịch sử. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-29** · OPEN · later · P3 · owner: — — Benchmark chuyên sâu. Nguồn: plans.md §1 · Lịch: —
- **BL-THANH-30** · OPEN · later · P3 · owner: — — Risk rule cho burst/rapid edits. Nguồn: plans.md §2 · Lịch: —
