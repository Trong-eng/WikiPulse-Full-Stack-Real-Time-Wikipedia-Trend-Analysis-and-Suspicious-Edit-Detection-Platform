Trạng thái: DONE · Owner: Thành · Reviewer: Subagent mỗi pha · Liên quan: báo cáo kỹ thuật WikiPulse

## Mục tiêu
Tạo bài PowerPoint 12 slide cho 10–15 phút từ báo cáo kỹ thuật, kèm lời thoại mỗi slide và ảnh dashboard thật.

## Phạm vi / Không làm
Nội dung lấy từ báo cáo; chạy hệ thống để chụp dashboard. Không thay đổi code, contract hoặc dùng ảnh giao diện giả. PowerPoint dùng các đối tượng có thể chỉnh sửa; ảnh dashboard là ảnh chụp thật.

## Các bước
- [x] Đối chiếu báo cáo, chụp dashboard bằng @Browser, xác nhận ảnh và vị trí; subagent review.
- [x] Dựng bố cục chỉnh sửa được theo phong cách đã chọn; subagent review.
- [x] Hoàn thiện 12 slide và lời thoại; subagent review nội dung, số liệu và thuật ngữ.
- [x] Kiểm tra hình ảnh, số liệu, lời thoại và review bản trình bày; cung cấp bản Spaces để tải PowerPoint.

## Quyết định
- Ưu tiên dữ liệu LIVE và bổ sung REPLAY khi cần, ghi rõ nguồn; giữ nguyên giới hạn phép đo trong báo cáo.
- Dựng chữ và sơ đồ thành các đối tượng chỉnh sửa được; giữ ảnh dashboard gốc và lời thoại trong speaker notes.

## Nhật ký
- 2026-11-25 — Bắt đầu chuẩn bị nội dung, dashboard và bố cục theo plan đã thống nhất.
- 2026-11-25 — Khởi động stack LIVE cô lập; chụp Overview bằng @Browser, số liệu enwiki tạm tính. Không lưu ảnh Trending vì có tiêu đề chứa username. Chờ subagent review và xác nhận ảnh dùng cho slide 9.
- 2026-11-25 — Subagent đối chiếu bố cục và hai ảnh Overview: số liệu khớp báo cáo, không thấy username/IP; bổ sung phạm vi bộ mẫu, giải thích ảnh LIVE theo wiki và cửa sổ, lưu ý trục thời gian nhỏ. Đã dọn stack và volume demo riêng.
- 2026-11-25 — Thành đồng ý dùng ảnh Overview LIVE cho slide 9 và tiếp tục sang bước chọn phong cách.
- 2026-11-25 — Thành chọn phong cách học thuật, sáng rõ: nền sáng, xanh dương/xanh ngọc, chữ lớn và sơ đồ thoáng. Công cụ tạo ảnh tích hợp có sẵn; chờ xác nhận backend trước khi tạo slide mẫu theo codex-ppt.
- 2026-11-25 — Thành đồng ý chuyển từ codex-ppt sang PowerPoint chỉnh sửa được; giữ bố cục, ảnh dashboard, lời thoại và review theo pha.
- 2026-11-25 — Dựng bìa bằng các ô chữ chỉnh sửa được; subagent review ảnh render, xác nhận bố cục và thông tin, đề nghị bổ sung ý xu hướng và ưu tiên chỉnh sửa. Đã sửa phụ đề theo review.
- 2026-11-25 — Dựng 12 slide và notes, hai subagent review nội dung và ảnh render. Đã sửa sơ đồ xử lý ba tầng, luồng phát lại và mũi tên; giải thích HDFS, tăng diện tích ảnh dashboard. Notes gồm khoảng 1.268 từ và được lưu thêm trong `artifacts/wikipulse-slides/loi-thoai.md`.
- 2026-11-25 — Subagent review cuối xác nhận 12 slide, notes và các shape riêng; slide 9 có ảnh dashboard thật, nhãn trục nhỏ nên chỉ dùng minh họa. Bản trình bày Spaces cho phép người dùng tải PowerPoint; chưa kiểm chứng file sau khi tải.
- 2026-11-25 — Sao chép lời thoại vào `docs/bao-cao-ky-thuat/loi-thoai-slide.md`; đang chờ Thành tải PPTX. Rà soát sơ đồ draw.io trong báo cáo: phù hợp nhất là kiến trúc cho slide 4 và luồng xử lý cho slide 6; sơ đồ xác nhận/kết nối lại có thể dùng giản lược cho slide 5, sơ đồ triển khai có thể hỗ trợ slide 8 nếu cần giải thích sâu.
- 2026-11-25 — Thành yêu cầu cập nhật các sơ đồ (kể cả triển khai), đồng bộ lời thoại và gọi hai subagent review. Dựng sơ đồ slide bằng shape chỉnh sửa được, dựa trên sơ đồ draw.io của báo cáo.
- 2026-11-25 — Hai subagent review bốn sơ đồ và lời thoại; bổ sung Gold, điều kiện ghi analytics vào Cassandra, đổi tên slide 5. Đã xuất PPTX có 12 slide, 12 Notes khớp kịch bản, xác nhận shape riêng qua cấu trúc tệp và mở kiểm tra slide 4 trong PowerPoint.
- 2026-11-25 — Theo chỉnh lại của Thành, thay sơ đồ vẽ lại ở slide 4, 5, 6, 8 bằng ảnh xuất trực tiếp từ PDF sơ đồ báo cáo, đồng bộ lời thoại. Hai subagent đối chiếu hình và nội dung; đã phóng to và giải thích thuật ngữ, nhưng một số đường nối và nhãn slide 6 vẫn nhỏ khi trình chiếu.

## Kết quả
Bản trình bày: [PowerPoint](../bao-cao-ky-thuat/slide-wikipulse.pptx) và [kịch bản](../bao-cao-ky-thuat/loi-thoai-slide.md); bản trực tuyến: Spaces page `page_33cbfd77d1308191a59569000307fd1c`. Kiểm tra cấu trúc PPTX: 12 slide, 12 Notes khớp kịch bản; ảnh trên từng slide 4, 5, 6, 8 có SHA-256 trùng ảnh xuất từ PDF tương ứng. Hai subagent review hình render và nội dung. Bản PPTX mới chưa được kiểm tra trực tiếp trong PowerPoint; một số đường nối và nhãn trong hình gốc, đặc biệt slide 6, nhỏ khi trình chiếu.
