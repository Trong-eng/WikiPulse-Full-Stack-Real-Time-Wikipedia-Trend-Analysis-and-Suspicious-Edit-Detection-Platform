Trạng thái: DONE · Owner: Thành · Reviewer: subagent; Thành · Liên quan: W1-THANH-01–W4-THANH-01

## Mục tiêu

Viết tài liệu giải thích ingestion/replay W1–W4 để hỗ trợ Thành bổ sung báo cáo kỹ thuật, dựa trên code và evidence đã có.

## Phạm vi / Không làm

Viết `docs/thanh/ingestion-replay-bao-cao.md`; không thay code, contract, checkpoint hay báo cáo LaTeX của Nhân. Trạng thái, lệnh và evidence chi tiết vẫn ở nguồn chuẩn; không commit dữ liệu LIVE hay danh tính thật.

## Các bước

- [x] Pha 1: đối chiếu nguồn, lập khung; subagent review.
- [x] Pha 2: viết thiết kế, sơ đồ Mermaid; subagent đối chiếu code.
- [x] Pha 3: phân tích kết quả và giới hạn metric; subagent đối chiếu evidence.
- [x] Pha 4: biên tập, kiểm tra link/privacy/Mermaid; subagent đọc toàn bài.

## Quyết định

- Tài liệu cá nhân là ghi chú tổng hợp kiến thức kỹ thuật, dẫn nguồn về plan/contract; không thay nguồn chuẩn hoặc tự đánh giá checkpoint nhóm.
- Dùng dữ liệu tổng hợp trong ví dụ; không coi các lượt thử khác môi trường là benchmark so sánh.

## Nhật ký

- 2026-11-23 — Bắt đầu theo plan bốn pha; đối chiếu checkpoint, contract, code và report LaTeX hiện có.
- 2026-11-23 — Review pha 1: khung đủ W1–W4; nhấn mạnh fixture W1 và kiểm chứng cá nhân, không suy ra CP1 nhóm DONE hoặc trạng thái Git hiện tại từ nhật ký cũ.
- 2026-11-23 — Review pha 2: đối chiếu code và sơ đồ; sửa ví dụ replay để phân biệt khoảng chờ tính toán với thời gian gửi thực tế, bổ sung privacy của LIVE raw và dòng fixture sai có chủ đích.
- 2026-11-23 — Review pha 3: số liệu và ngoại suy khớp evidence; làm rõ `parse_errors` không kiểm schema và phép đo catch-up được quan sát theo nhịp thăm dò, tập dữ liệu dùng một partition.
- 2026-11-23 — Review pha 4: không thấy lỗi nghiêm trọng; bổ sung giải thích offset, query, checkpoint và watermark, nêu rõ 8,984 giây không phải độ trễ từng sự kiện. Kiểm tra link nội bộ thành công; Mermaid được kiểm tra cấu trúc fence và đọc tĩnh, chưa render bằng parser chuyên dụng.

## Kết quả

- [Báo cáo ingestion/replay](../thanh/ingestion-replay-bao-cao.md) có hai sơ đồ Mermaid và phân tích evidence W1–W4; bốn lượt review độc lập đã hoàn tất.
- Kiểm tra file mới bằng Python đọc UTF-8, dò link Markdown/heading và đếm fence Mermaid: `LINK_ERRORS=0 MERMAID_BLOCKS=2 FENCES=4`. Kiểm tra lại fence: `.\.venv\Scripts\python.exe -c "from pathlib import Path; s=Path('docs/thanh/ingestion-replay-bao-cao.md').read_text(encoding='utf-8'); print(s.count(chr(96)*3+'mermaid'), s.count(chr(96)*3))"` → `2 4`.
- `git diff --check` → exit 0; file mới chưa tracked nên kiểm tra thêm khoảng trắng trực tiếp khi đọc file. Chưa có Mermaid parser cục bộ, sơ đồ đã được review tĩnh chứ chưa render tự động. Không chạy test code vì chỉ thêm tài liệu.
