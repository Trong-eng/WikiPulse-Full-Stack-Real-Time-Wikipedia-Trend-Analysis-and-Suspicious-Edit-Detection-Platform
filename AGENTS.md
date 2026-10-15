# AGENTS.md — quy trình làm việc WikiPulse

Áp dụng cho mọi thành viên và mọi AI agent (Codex đọc file này; Claude Code đọc qua `CLAUDE.md`). Mục tiêu: ai mở repo cũng biết việc gì đã làm, việc gì còn treo, và mỗi chủ đề được ghi ở đúng một file. File này chỉ chứa quy tắc. Lệnh chạy, contract, tiến độ nằm ở các file trong bản đồ docs bên dưới.

## 1. Đọc trước khi làm

[plans.md](plans.md) → [docs/checkpoints.md](docs/checkpoints.md) → [docs/backlog.md](docs/backlog.md) (mục của bạn và "Cần nhóm quyết định") → [docs/contracts.md](docs/contracts.md) → README của module sắp sửa → plan của việc đó trong `docs/plans/`.

Khi các file mâu thuẫn nhau:
- Về quy trình (cách ghi docs, plan, backlog, branch): `AGENTS.md` > `docs/development.md` / `README.md`.
- Về kỹ thuật: `contracts.md` > `checkpoints.md` > plan của từng việc; `plans.md` là khung tổng.

Làm theo bên có ưu tiên cao hơn, đồng thời ghi item backlog cho owner của file thấp hơn. Riêng mâu thuẫn liên quan **contract** thì dừng lại và hỏi producer/consumer trước khi code.

## 2. Quy trình một việc

1. **Tìm việc**: việc có lịch nằm trong checkpoints; việc chưa có lịch nằm trong backlog. Nếu việc đã có item thì ghi ID item đó vào plan.
2. **Plan trước khi code**: mở hoặc tạo plan (mục 3). Việc nhỏ (sửa typo, fix một dòng, chạy lại test) chỉ cần thêm một dòng Nhật ký vào **plan đang làm**. "Plan đang làm" là plan ACTIVE/REVIEW gần nhất của bạn liên quan tới việc đó; nếu không có thì dùng một file duy nhất `docs/plans/<owner>-misc.md`. Không có việc nào được bỏ qua bước ghi chép.
3. **Làm và kiểm chứng**: test trước, rồi chạy lại các lệnh trong README/development. Evidence phải là lệnh và output tái hiện được.
4. **Docs cùng PR**: chạy checklist ở mục 5. Docs lệch code là lỗi, xử lý như bug.
5. **Đóng vòng**:
   - Cập nhật trạng thái các item backlog mà bạn là owner. Thêm item cho việc phát sinh mà chưa làm.
   - Nếu checkpoint đổi trạng thái, ô Evidence chỉ ghi link tới plan.
   - Điền mục Kết quả trong plan.

## 3. Plan

- **Khi nào tạo file mới**: việc là một checkpoint item; hoặc việc đổi contract hay config dùng chung; hoặc việc kéo dài hơn một phiên làm việc. Các trường hợp còn lại ghi vào Nhật ký của plan đang làm.
- **Tên file**: `docs/plans/<ID>.md` cho checkpoint item (ví dụ `W1-THANH-01.md`). `docs/plans/<owner>-<slug>.md` cho việc ngoài checkpoint, lộ trình cá nhân, hoặc `<owner>-misc.md`. Một việc chỉ có một plan; không tạo file theo ngày hay theo phiên.
- **Template** (gói trong một màn hình; lộ trình cá nhân chỉ bắt buộc có dòng đầu):
  - dòng đầu: `Trạng thái: ACTIVE | REVIEW | BLOCKED | DONE · Owner · Reviewer · Liên quan: <ID checkpoint/BL>` (ACTIVE tương ứng IN_PROGRESS của checkpoint);
  - các mục: `## Mục tiêu` · `## Phạm vi / Không làm` · `## Các bước` (checkbox) · `## Quyết định` (quyết định chờ nhóm thì link item BL) · `## Nhật ký` (`- YYYY-MM-DD — việc — PR/commit`) · `## Kết quả` (evidence, lệnh tái hiện).
- **Vòng đời**: khi checkpoint DONE thì plan chuyển DONE và giữ nguyên, không xóa. Sửa về sau thì thêm dòng Nhật ký mới.

## 4. Bản đồ docs — mỗi chủ đề một nơi

| Chủ đề | File / pattern | Owner |
|---|---|---|
| Kế hoạch tổng, phân công 4 tuần | `plans.md` | Trọng |
| Việc có lịch, trạng thái, link evidence | `docs/checkpoints.md` | owner từng dòng; Trọng tổng hợp |
| Việc chưa có lịch, quyết định chờ chốt, nợ kỹ thuật, phát hiện cross-team, sau MVP | `docs/backlog.md` | người tạo item / owner item |
| Contract giữa module, kể cả bản nháp | `docs/contracts.md` (nháp: sửa thẳng trên PR draft) | producer + consumer |
| Kiến trúc, luồng dữ liệu, data dictionary | `docs/architecture.md`, `docs/data-flow.md`, `docs/data-dictionary.md` | Trọng; owner module sửa phần của mình |
| Setup, lệnh chạy, branch, ownership | `README.md`, `docs/development.md` | Trọng |
| Lịch sử nghiệm thu CP0 (đóng băng) | `docs/verification.md`, `docs/implementation-log.md` | Trọng |
| Plan, nhật ký, kết quả từng việc | `docs/plans/<ID>.md`, `docs/plans/<owner>-<slug>.md` | owner |
| Khảo sát nguồn hoặc công cụ bên ngoài | `docs/<chủ-đề>-spike.md` | người làm spike |
| Cách chạy, flags, giới hạn của module | `<module>/README.md` (kể cả thư mục con, ví dụ `storage/cassandra/README.md`) | owner module |
| Báo cáo LaTeX (sau khi merge branch `nhan/bao-cao-ky-thuat`) | `docs/bao-cao-ky-thuat/` | Nhân; mỗi owner viết mục của mình |
| Quy trình cho người và agent | `AGENTS.md`, `CLAUDE.md` (chỉ `@AGENTS.md`) | Trọng |

**Tạo file `.md` mới**:
- Trước khi tạo, tìm trong bảng trên. Nếu chủ đề đã có file thì ghi vào file đó.
- Chỉ tạo file mới khi khớp một pattern có sẵn trong bảng; khi đó không cần sửa AGENTS.md.
- Một *loại* tài liệu mới, hoặc một file nằm ngoài các pattern, phải thêm dòng vào bảng này **trong cùng PR**.
- Ghi chú cá nhân không commit: Claude Code dùng `CLAUDE.local.md`. Codex không có file tương đương, nên để ngoài repo.

## 5. Checklist "docs theo kịp code" (mỗi PR)

- [ ] Đổi flag, lệnh chạy, exit code, biến môi trường → sửa README của module (và `.env.example` nếu là biến mới; file này do Trọng quản lý, mở item backlog nếu không phải bạn).
- [ ] Đổi schema, payload, API hay hành vi mà module khác dùng → sửa `docs/contracts.md` + có review của cả producer lẫn consumer.
- [ ] Đổi luồng dữ liệu hoặc thêm thành phần → sửa architecture/data-flow, hoặc mở item cho Trọng.
- [ ] Plan có Nhật ký + Kết quả; checkpoint chỉ link tới plan.
- [ ] Backlog: đóng item đã xử lý (`DONE (PR #…)`), thêm item phát sinh.
- [ ] Không chép cùng một nội dung sang nhiều file. Ghi ở một chỗ, các chỗ khác link tới.

## 6. Quy tắc cứng

- **Ownership**: chỉ sửa file thuộc module của mình (xem bảng ownership trong `README.md`/`docs/development.md`). Thấy file của người khác sai hoặc lệch: thêm item backlog vào mục của owner, không tự sửa.
- **Contract**: thay đổi phải được producer và consumer review.
- **DONE**: chỉ đánh DONE khi có evidence chạy lại được. Không đánh DONE thay người khác.
- **Privacy**: không đưa username/IP thật vào API, docs, fixture hay log được commit. Dữ liệu LIVE muốn commit phải được pseudonymize và có test chặn lộ.
- **Git**: AI agent không commit hay push khi người dùng chưa cho phép. Branch đặt tên `<owner>/<ID>-<slug>`, ví dụ `thanh/w2-thanh-01-sse-collector`. Mỗi PR làm một việc có đầu ra kiểm thử được.

## 7. Không làm

- Không tạo file nháp, file review hay file log song song với file đích. Ví dụ: `contracts-w2-draft.md` thay vì sửa `contracts.md`; `xxx-review.md` thay vì plan của checkpoint.
- Không đưa trạng thái tiến độ, lệnh chạy hay nội dung contract vào AGENTS.md; những thứ này link sang file tương ứng.
- Không xóa hay viết lại item backlog, dòng checkpoint hoặc Nhật ký của người khác. Chỉ thêm ghi chú. Ngoại lệ: owner của item backlog được đổi trạng thái và `Lịch:` (xem quy tắc trong `docs/backlog.md`).
