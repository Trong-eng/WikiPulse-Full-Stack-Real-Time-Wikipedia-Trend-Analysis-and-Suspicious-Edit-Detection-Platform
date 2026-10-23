# thanh-agents-backlog — Quy trình AGENTS.md + docs/backlog.md

Trạng thái: REVIEW · Owner: Thành · Reviewer: Trọng (bắt buộc, vùng docs tích hợp), Nhân, Linh · Liên quan: [BL-THANH-13](../backlog.md#trọng), BL-THANH-31, BL-THANH-32

## Mục tiêu

Mọi người và AI agent ghi việc vào cùng một chỗ. Mỗi việc có plan để người khác biết đã làm gì. Việc chưa giải quyết nằm ở `docs/backlog.md`. Docs được sửa cùng PR với code. Không ai tạo file md trùng chủ đề với file đã có.

## Phạm vi / Không làm

- Làm: `AGENTS.md`, `CLAUDE.md` (trỏ tới AGENTS.md), `docs/backlog.md` (seed), áp dụng thử cho W1-THANH-01.
- Không làm: sửa `docs/development.md`, `plans.md`, `docs/implementation-log.md`, `README.md`, `.gitignore` hay docs của người khác. Những chỗ cần đồng bộ được ghi thành item backlog cho owner. Ngoại lệ 16/10: Thành yêu cầu chuyển hai file lịch sử CP0 của Trọng vào `docs/trong/` (xem Quyết định).

## Các bước

- [x] Debate thiết kế với subagent phản biện. Thành chọn: bản đồ docs theo pattern, plan theo checkpoint ID, chung branch W1, có CLAUDE.md 1 dòng.
- [x] Viết AGENTS.md, CLAUDE.md, docs/backlog.md.
- [x] Viết docs/plans/W1-THANH-01.md; checkpoints chỉ còn link tới plan.
- [x] Subagent review (không có Critical), sửa toàn bộ finding Important.
- [x] Thêm folder docs theo người (`docs/<owner>/`): sửa AGENTS.md §4, chuyển `docs/ingestion-spike.md` → `docs/thanh/ingestion-spike.md`, cập nhật link, backlog và script kiểm docs.
- [ ] Trọng và nhóm review các commit đã push lên `main`; Trọng là owner AGENTS.md.

## Quyết định

- ID backlog theo người tạo (`BL-<NGƯỜI>-NN`) để không trùng giữa các branch. Backlog viết dạng danh sách chia theo người xử lý, đóng item tại chỗ. Item giao cho người khác bắt đầu ở `PROPOSED`.
- Plan theo checkpoint ID; việc nhỏ ghi vào Nhật ký. Mỗi sự kiện chỉ viết ở một chỗ, các nơi khác chỉ link tới.
- Nháp contract sửa thẳng `docs/contracts.md` trên PR draft.
- Docs theo người (Thành yêu cầu, 16/10): tài liệu do một người viết và chịu trách nhiệm nằm ở `docs/<owner>/` (`trong`, `thanh`, `linh`, `nhan`, `manh`). Tài liệu chung (plans, backlog, checkpoints, contracts, architecture, …) vẫn ở `docs/`. Plan vẫn ở `docs/plans/` vì checkpoints và backlog link tới đó theo ID. File riêng của Trọng (`verification.md`, `implementation-log.md`, lịch sử CP0) chuyển vào `docs/trong/` theo yêu cầu trực tiếp của Thành ngày 16/10; các file Trọng là owner nhưng cả nhóm làm theo (`development.md`, `architecture.md`, `data-flow.md`, `data-dictionary.md`, `contracts.md`, `checkpoints.md`) giữ ở gốc. Trọng duyệt ([BL-THANH-32](../backlog.md#trọng)). Không tạo sẵn folder rỗng cho người khác.
- AGENTS.md đã lên `main` (Thành fast-forward và push ngày 15/10), nên theo bản đồ docs Trọng là owner. Thay đổi docs theo người làm theo yêu cầu trực tiếp của Thành. Ngày 16/10 Thành chọn push thẳng lên `main`, không qua PR, nên **Trọng review sau khi push** (xem commit trên `main`; không đồng ý thì revert).
- **Ngoại lệ đã chốt**: việc này nằm chung branch `thanh/w1-ingestion-replay-takeover` với W1-THANH-01 vì Thành chọn vậy. Branch này có trước convention `<owner>/<ID>-<slug>`, và PR sẽ chứa hai việc. Từ việc sau sẽ theo đúng AGENTS.md.

## Nhật ký

- 2026-10-15 — thiết kế, debate, viết bản đầu, review, sửa finding — commit `docs: add AGENTS.md process and backlog` trên branch `thanh/w1-ingestion-replay-takeover` (chưa push)
- 2026-10-15 — Thành fast-forward `thanh/w1-ingestion-replay-takeover` vào `main` và push; `origin/main` = `6951779`
- 2026-10-16 — thêm quy tắc docs theo người `docs/<owner>/`, chuyển spike vào `docs/thanh/`, sửa link và script kiểm docs; sửa lỗi có sẵn BL-13/BL-31 bị chèn lẫn; thêm BL-THANH-32. Subagent review: siết tiêu chí tầng chung / folder riêng, dòng `docs/<owner>/` không dùng cho plan/review/nhật ký, script in UTF-8 — commit `docs: per-owner docs folders, move ingestion spike to docs/thanh`
- 2026-10-16 — theo yêu cầu Thành: tạo `docs/trong/`, chuyển `verification.md` và `implementation-log.md` vào đó; sửa tham chiếu trong `docs/checkpoints.md` (2 dòng của Trọng), `docs/trong/implementation-log.md`, AGENTS.md §4, backlog BL-13/BL-32 và script kiểm docs
- 2026-10-16 — Thành cho phép commit và push thẳng lên `main` (sau khi fast-forward PR #1, #2 của Nhân); ghi chú BL-07, BL-22 — commit `docs: per-owner docs folders, move ingestion spike to docs/thanh`
- 2026-10-23 — theo yêu cầu Thành: gộp 4 nhánh của nhóm vào `main` (local, chưa push); viết `tong-ket-1.md` (tổng kết tuần 1 cho cấp trên) với 2 subagent khảo sát, 1 subagent debate, 1 subagent review; thêm dòng `tong-ket-<N>.md` vào bảng bản đồ docs AGENTS.md §4 và các item BL-THANH-33..37; chạy lại toàn bộ test trên code đã gộp (BL-35 DONE); thêm mục 5 "Cách chạy lại" (local + Docker, từng lệnh đã chạy thử), ghi đề xuất `.ps1` vào BL-06; viết `scripts/wikipulse.ps1` theo yêu cầu Thành (chỉ chạy khi đã có `.venv`), chạy thử mọi target; subagent review, sửa 5 Important + 5 Minor — commit `docs: week-1 progress report, Windows ps1 runner`
- 2026-10-23 — theo yêu cầu Thành: `tong-ket-1.md` bỏ cột "Mức" (trạng thái nghiệm thu/review) và mục Rủi ro; mục "Cách chạy lại" thành mục 4; sửa 2 link trong backlog — commit `docs(tong-ket-1): drop status column and risk section`

## Kết quả

[AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md), [backlog.md](../backlog.md) (32 item). Kiểm chứng: không có link tương đối hay anchor nào chết; mọi file `*.md` khớp bản đồ docs; không có ID backlog trùng; suite code không đổi (114 passed).

16/10 (sau khi thêm `docs/<owner>/`): script ra `broken links: none`, `not in doc map: none`, `duplicate BL ids: none`; negative test (thêm `docs/stray-note.md` và một link chết trong `docs/thanh/`) bị bắt đúng cả hai.

Script kiểm tạm, chạy từ root repo bằng `.venv\Scripts\python check_docs.py`. Đưa vào `scripts/` là việc của [BL-THANH-31](../backlog.md#trọng).

```python
import collections, re, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # in được anchor tiếng Việt trên console cp1252

files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
files = [f for f in files if Path(f).exists()]  # bỏ file đã xóa/chuyển nhưng còn trong index
slug = lambda h: re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")  # GitHub anchor
broken = []
for f in files:
    for target in re.findall(r"\]\(([^)\s]+)\)", Path(f).read_text(encoding="utf-8")):
        if target.startswith(("http", "#")):
            continue
        path, _, anchor = target.partition("#")
        dest = (Path(f).parent / path).resolve()
        if not dest.exists():
            broken.append((f, target))
        elif anchor and dest.suffix == ".md":
            heads = re.findall(r"^#+\s+(.*)$", dest.read_text(encoding="utf-8"), re.M)
            if anchor not in {slug(h) for h in heads}:
                broken.append((f, target))
patterns = [r"(.+/)?README\.md", r"plans\.md", r"tong-ket-\d+\.md", r"AGENTS\.md", r"CLAUDE\.md", r"docs/plans/[^/]+\.md",
            r"docs/(checkpoints|backlog|contracts|architecture|data-flow|data-dictionary|development)\.md",
            r"docs/(trong|thanh|linh|nhan|manh)/[a-z0-9-]+\.md",
            r"docs/bao-cao-ky-thuat/.*"]
ids = re.findall(r"\*\*(BL-[A-Z]+-\d+)\*\*", Path("docs/backlog.md").read_text(encoding="utf-8"))
print("broken links:", broken or "none")
print("not in doc map:", [f for f in files if not any(re.fullmatch(p, f) for p in patterns)] or "none")
print("duplicate BL ids:", [i for i, n in collections.Counter(ids).items() if n > 1] or "none")
```
