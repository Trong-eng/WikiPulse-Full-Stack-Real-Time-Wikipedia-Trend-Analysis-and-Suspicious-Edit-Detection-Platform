Trạng thái: DONE · Owner: Trọng · Reviewer: Trọng · Liên quan: CP0 (kiểm tra lại demo)

## Mục tiêu

Kiểm tra khả năng demo REPLAY trên máy hiện tại sau khi pull main `ca3d192`.

## Phạm vi / Không làm

Chạy kiểm tra môi trường và smoke test cô lập theo README. Không đổi code, contract hoặc trạng thái checkpoint; không commit/push.

## Các bước

- [x] Đọc README, checkpoints, backlog, contracts và script smoke.
- [x] Kiểm tra Git, Python và Docker.
- [x] Khởi động Docker nếu khả dụng; chạy smoke REPLAY.
- [x] Ghi kết quả thực tế và giới hạn demo.

## Quyết định

Dùng smoke với project/volume riêng để tránh trộn dữ liệu demo vào dữ liệu dev.

## Nhật ký

- 2026-11-23 — Soạn [báo cáo hạ tầng và tích hợp W1–W4](../trong/ha-tang-tich-hop-bao-cao.md) trên `main` theo bố cục báo cáo của Thành. Đối chiếu số liệu với hồ sơ CP0 và các plan W2–W4, kiểm tra liên kết và sơ đồ trước khi bàn giao.
- 2026-11-23 — `git fetch --all --prune --tags` thêm 5 nhánh remote của Nhân/Thành; `git pull --ff-only origin main` fast-forward `0c59b03` → `a691238` (12 commit). `git rev-list --left-right --count main...origin/main` trả `0 0`; các nhánh local Trọng W2/W3/W4 cũng khớp remote.
- 2026-11-23 — Theo yêu cầu của Trọng, `git push --atomic origin main` cùng ba nhánh Trọng W2/W3/W4 trả exit 0. Đối chiếu `git ls-remote --heads origin` xác nhận `main` và W4 ở `0c59b03`, W3 ở `7db6682`, W2 ở `312c086`; local `main` khớp `origin/main`.
- 2026-11-23 — Fetch toàn bộ nhánh/tag, pull `main` bằng fast-forward và đối chiếu nhánh đang có với `main` theo lịch sử Git và patch tương đương.
- 2026-11-05 — Theo yêu cầu của Trọng: fetch toàn bộ remote branches/tags, cập nhật main bằng fast-forward nếu có, rồi mô phỏng merge nhánh `linh-week2` vào main bằng `git merge-tree --write-tree`; ghi SHA và conflict thực tế. Giữ file local đang có; không merge thật, commit hoặc push.
- 2026-10-25 — Kiểm tra yêu cầu demo sau khi pull main `ca3d192`; Python `.venv` 3.12.5 có sẵn, Docker daemon chưa chạy. Chưa commit/push.
- 2026-10-25 — Mở Docker Desktop (Engine 29.2.1), build lại 4 image và chạy `.venv/bin/python scripts/smoke_test.py --keep`: exit 0, `status=passed`. Giữ stack cô lập để xem demo; không đổi checkpoint chung.
- 2026-10-26 — Theo yêu cầu của Trọng, tạo bộ 8 slide báo cáo dựa trên kịch bản đã thống nhất, không có lời trình bày hay ghi chú diễn giả. Nguồn: `tong-ket-1.md`, `docs/checkpoints.md`, evidence smoke 25/10 và ảnh dashboard trong báo cáo kỹ thuật. Đã render và kiểm tra từng slide, xác nhận 8 slide và 0 ghi chú có nội dung. Bản chỉnh sửa trực tiếp: `artifact_uGTAlHC7ut_yz_6PoAlICp9nEiew5t8j`. Không commit/push.
- 2026-10-26 — Theo yêu cầu tiếp theo, đã dịch nội dung và bảng biểu của 8 slide sang tiếng Anh, giữ số liệu và bố cục, không thêm ghi chú diễn giả. Đã render kiểm tra cả 8 slide và xác nhận 0 ghi chú có nội dung trong cùng artifact. Giữ ảnh dashboard tiếng Việt làm bằng chứng gốc, có chú thích tiếng Anh ghi rõ. Không commit/push.
- 2026-10-26 — Theo yêu cầu bổ sung, đã làm rõ sơ đồ kiến trúc từ ảnh đính kèm bằng ImageGen và chèn vào slide 2 của bản tiếng Anh. Ảnh, prompt và kịch bản tiếng Việt lưu ở `artifacts/presentations/wikipulse-2026-10-26/` (local, gitignore). Đã render kiểm tra slide thay đổi và toàn bộ bố cục: vẫn 8 slide, 0 ghi chú có nội dung. Giữ LIVE là kế hoạch, REPLAY là luồng đã kiểm chứng. Không đổi code/contract/checkpoint, không commit/push.

## Kết quả

Ngày 23/11/2026 — [Báo cáo hạ tầng và tích hợp](../trong/ha-tang-tich-hop-bao-cao.md) có 8 mục. Kiểm tra từ tệp Markdown bằng Python (`pathlib`, đối chiếu đường dẫn và tiêu đề) xác nhận đủ 40 liên kết hợp lệ. `mermaid.parse` trên hai khối sơ đồ trả `flowchart-v2` và `sequence`. Đối chiếu report JSON gốc của smoke W3 và clone sạch W4 đều ghi `passed` và 9 truy vấn phục hồi.

Kiểm tra merge ngày 2026-11-23:

- `git fetch --all --prune --tags` tải thêm hai nhánh Linh W3/W4. `git pull --ff-only origin main` trả `Already up to date.`; `git rev-list --left-right --count main...origin/main` trả `0 0` tại `312c086`.
- `git branch --remotes --no-merged main` chỉ trả `origin/linh/w3-linh-01-hdfs` và `origin/linh/w4-linh-01-correctness` (9/11 nhánh remote ngoài main đã vào main). `git cherry -v main origin/linh/w4-linh-01-correctness` trả `+ a38d51d…` và `+ d818855…`; không thấy patch tương đương trên main.
- `git merge-base --is-ancestor origin/linh/w3-linh-01-hdfs origin/linh/w4-linh-01-correctness` exit 0. W4 chứa W3 và thêm `d818855`. Chỉ cập nhật từ remote và kiểm tra, không merge hai nhánh này.

Kiểm tra merge ngày 2026-11-05:

- `git fetch --all --prune --tags`: exit 0, đã tải các nhánh remote; tên nhánh tuần 2 thực tế là `origin/linh/w2-linh-01-analytics`.
- `git pull --ff-only origin main`: exit 0, `Already up to date.`; main local/remote cùng SHA `ca3d192bd8be6ddc5f0a52c3634c267834cf3021`.
- Head Linh: `78acbf672afdd78fa0e515891593ad193ba815b0`. `git rev-list --left-right --count origin/main...origin/linh/w2-linh-01-analytics` trả `0 1`: nhánh Linh hơn main đúng một commit, main không có commit riêng.
- `git merge-tree --write-tree --name-only ca3d192bd8be6ddc5f0a52c3634c267834cf3021 78acbf672afdd78fa0e515891593ad193ba815b0`: exit 0, chỉ trả tree `34471fde4aac7fa8337b714d87fc5cb18567e8f3`, không có file conflict; có thể fast-forward.
- Phạm vi kết luận là conflict Git; không chạy lại unit/Spark/E2E trong lần kiểm tra này. Chưa merge nhánh Linh vào main, không commit/push. File local có sẵn được giữ nguyên ngoài phần nhật ký/kết quả bổ sung này; không đổi checkpoint/backlog của người khác.

Lệnh tái hiện: `.venv/bin/python scripts/smoke_test.py --keep` (Docker Desktop phải chạy).

Evidence: [report.json](../../artifacts/smoke-20261025140749-d8882cace5804faa84d248a1b6688615/report.json), [commands.log](../../artifacts/smoke-20261025140749-d8882cace5804faa84d248a1b6688615/commands.log), [services.log](../../artifacts/smoke-20261025140749-d8882cace5804faa84d248a1b6688615/services.log). Đây là artifact local được gitignore.

Đạt: API/UI readiness; activity hai wiki; dashboard counts/window/readiness; dedup/invalid/canary; Bronze/Silver/Gold; ba endpoint chưa triển khai trả 501 đúng contract.

Địa chỉ trong lần chạy này: dashboard `http://127.0.0.1:55002`, API `http://127.0.0.1:55001`. Dữ liệu REPLAY lịch sử; Overview và System Status hoạt động; LIVE, Trending, Suspicious Edits chưa triển khai.

Stack giữ lại bằng `--keep`. Khi xem xong, dừng và dọn riêng lần kiểm tra này bằng `docker compose -p wikipulse-smoke-20261025140749-d8882cace5804faa84d248a1b6688615 down --volumes --remove-orphans`. Không chạy lệnh dọn với project mặc định.
