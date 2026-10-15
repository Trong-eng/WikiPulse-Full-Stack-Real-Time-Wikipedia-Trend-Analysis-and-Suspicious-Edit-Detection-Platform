# thanh-agents-backlog — Quy trình AGENTS.md + docs/backlog.md

Trạng thái: REVIEW · Owner: Thành · Reviewer: Trọng (bắt buộc, vùng docs tích hợp), Nhân, Linh · Liên quan: [BL-THANH-13](../backlog.md#trọng), BL-THANH-31

## Mục tiêu

Mọi người và AI agent ghi việc vào cùng một chỗ. Mỗi việc có plan để người khác biết đã làm gì. Việc chưa giải quyết nằm ở `docs/backlog.md`. Docs được sửa cùng PR với code. Không ai tạo file md trùng chủ đề với file đã có.

## Phạm vi / Không làm

- Làm: `AGENTS.md`, `CLAUDE.md` (trỏ tới AGENTS.md), `docs/backlog.md` (seed), áp dụng thử cho W1-THANH-01.
- Không làm: sửa `docs/development.md`, `plans.md`, `docs/implementation-log.md`, `README.md`, `.gitignore` hay docs của người khác. Những chỗ cần đồng bộ được ghi thành item backlog cho owner.

## Các bước

- [x] Debate thiết kế với subagent phản biện. Thành chọn: bản đồ docs theo pattern, plan theo checkpoint ID, chung branch W1, có CLAUDE.md 1 dòng.
- [x] Viết AGENTS.md, CLAUDE.md, docs/backlog.md.
- [x] Viết docs/plans/W1-THANH-01.md; checkpoints chỉ còn link tới plan.
- [x] Subagent review (không có Critical), sửa toàn bộ finding Important.
- [ ] Trọng và nhóm review PR; sau khi merge Trọng là owner AGENTS.md.

## Quyết định

- ID backlog theo người tạo (`BL-<NGƯỜI>-NN`) để không trùng giữa các branch. Backlog viết dạng danh sách chia theo người xử lý, đóng item tại chỗ. Item giao cho người khác bắt đầu ở `PROPOSED`.
- Plan theo checkpoint ID; việc nhỏ ghi vào Nhật ký. Mỗi sự kiện chỉ viết ở một chỗ, các nơi khác chỉ link tới.
- Nháp contract sửa thẳng `docs/contracts.md` trên PR draft.
- **Ngoại lệ đã chốt**: việc này nằm chung branch `thanh/w1-ingestion-replay-takeover` với W1-THANH-01 vì Thành chọn vậy. Branch này có trước convention `<owner>/<ID>-<slug>`, và PR sẽ chứa hai việc. Từ việc sau sẽ theo đúng AGENTS.md.

## Nhật ký

- 2026-10-15 — thiết kế, debate, viết bản đầu, review, sửa finding — commit `docs: add AGENTS.md process and backlog` trên branch `thanh/w1-ingestion-replay-takeover` (chưa push)

## Kết quả

[AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md), [backlog.md](../backlog.md) (31 item). Kiểm chứng: không có link tương đối hay anchor nào chết; mọi file `*.md` khớp bản đồ docs; không có ID backlog trùng; suite code không đổi (114 passed).

Script kiểm tạm, chạy từ root repo bằng `.venv\Scripts\python check_docs.py`. Đưa vào `scripts/` là việc của [BL-THANH-31](../backlog.md#trọng).

```python
import collections, re, subprocess
from pathlib import Path

files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
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
patterns = [r"(.+/)?README\.md", r"plans\.md", r"AGENTS\.md", r"CLAUDE\.md", r"docs/plans/[^/]+\.md",
            r"docs/(checkpoints|backlog|contracts|architecture|data-flow|data-dictionary|development"
            r"|verification|implementation-log)\.md", r"docs/[a-z0-9-]+-spike\.md", r"docs/bao-cao-ky-thuat/.*"]
ids = re.findall(r"\*\*(BL-[A-Z]+-\d+)\*\*", Path("docs/backlog.md").read_text(encoding="utf-8"))
print("broken links:", broken or "none")
print("not in doc map:", [f for f in files if not any(re.fullmatch(p, f) for p in patterns)] or "none")
print("duplicate BL ids:", [i for i, n in collections.Counter(ids).items() if n > 1] or "none")
```
