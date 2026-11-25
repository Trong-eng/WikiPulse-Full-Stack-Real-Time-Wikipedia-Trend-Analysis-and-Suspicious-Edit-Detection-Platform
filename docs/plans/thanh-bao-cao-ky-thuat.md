Trạng thái: REVIEW · Owner: Thành · Reviewer: Nhân, Trọng, Linh, Mạnh · Liên quan: W1–W4, CP1–CP4

## Mục tiêu

Cập nhật báo cáo LaTeX từ evidence của các thành viên; tách chapter, dùng thuật ngữ tiếng Anh chuẩn và sơ đồ draw.io chỉnh sửa được.

## Phạm vi / Không làm

Báo cáo chung trong `docs/bao-cao-ky-thuat/`; không thay code, contract, checkpoint hay tài liệu cá nhân. Không tự xác nhận review của owner hoặc nghiệm thu nhóm; không commit/push nếu chưa được yêu cầu.

## Các bước

- [x] Pha 1: đối chiếu nguồn và thuật ngữ; subagent khảo sát, phản biện và review.
- [x] Pha 2: tách chapter, cập nhật nội dung/glossary; subagent review.
- [x] Pha 3: chuyển sơ đồ sang draw.io và export; subagent review.
- [x] Pha 4: build, kiểm tra PDF trực quan; subagent review và bàn giao.

## Quyết định

- User yêu cầu draw.io thay quy ước TikZ trước đó; cập nhật README báo cáo cùng thay đổi. Tài liệu cá nhân giữ ở vị trí gốc; chỉ tổng hợp nội dung có nguồn, ghi rõ giới hạn.
- Glossary đứng trước abstract; một chapter một file `.tex`, entrypoint giữ preamble và bibliography. Không suy luận DONE từ code hoặc phép thử độc lập.

## Nhật ký

- 2026-11-25 — Bắt đầu theo plan bốn pha; phân công hai reviewer Spark độc lập và reviewer nguồn báo cáo.
- 2026-11-25 — Pha 1: hai reviewer Spark xác nhận canary, watermark theo event time, dedup giới hạn, unique editors xấp xỉ, risk heuristic và W3 7/7 chỉ theo fixture; review ba báo cáo lưu ý default analytics Parquet, clone sạch và EC2 là hai lượt riêng, một API request có thể đọc nhiều partition. Không suy CP3/CP4 DONE.
- 2026-11-25 — Pha 2: tách 11 file chapter/front matter; bản tách và bản cập nhật đã build XeLaTeX. Review code/evidence/văn phong phát hiện mô tả retry, Bronze, privacy, checkpoint và test API chưa chính xác: đã sửa theo code và plan; chuyển glossary lên trước quy ước, bổ sung thuật ngữ và loại mục trùng. Hình query độc lập sẽ sửa ở pha 3.
- 2026-11-25 — Pha 3: chuyển 12 hình cũ và bổ sung ACK/recovery thành 14 cặp draw.io/PDF; review phát hiện/sửa sai luồng Gold, thứ tự kiểm HDFS, chiều watermark và chồng chữ; reviewer kiểm lại các hình đã sửa. Build XeLaTeX đạt; còn review PDF tổng thể.
- 2026-11-25 — Pha 4: ba subagent xem toàn bộ 53 trang ban đầu và 52 trang sau chỉnh; tăng font 11 hình, sửa sơ đồ, trang mồ côi và bảng. Review nội dung phát hiện/sửa `provisional` của event detail, privacy page title và glossary. Build cuối 51 trang; hai subagent xem lại các trang thay đổi và mọi hình, không phát hiện blocker thị giác. Bìa và các mục chưa có thông tin giữ placeholder; chờ review của owner.
- 2026-11-25 — Cập nhật họ tên và MSSV năm thành viên trên trang bìa theo danh sách Thành cung cấp; biên dịch và kiểm tra lại trang bìa PDF.
- 2026-11-25 — Pull fast-forward từ `origin/docs` chứa báo cáo Linh và cập nhật dashboard của Mạnh. Gộp nội dung dashboard mới vào chapter tương ứng sau khi khôi phục bản tách chapter; build PDF 51 trang và kiểm tra trực quan trang dashboard.
- 2026-11-25 — Theo yêu cầu Thành, commit/push bản báo cáo nền `77561ea`; review xác nhận origin/main đã có báo cáo Linh và thay đổi dashboard của Mạnh. Bắt đầu bổ sung evidence W4 của Linh và làm rõ trạng thái dashboard; không thay checkpoint.
- 2026-11-25 — Hai reviewer đối chiếu evidence Linh và dashboard với code/plan; làm rõ risk tối đa 60, thêm glossary. XeLaTeX build exit 0, PDF 52 trang; subagent xem các trang glossary, evidence và kết luận đã render, không thấy lỗi cắt/chồng hoặc trang mồ côi.

## Kết quả

- Báo cáo: [main.pdf](../bao-cao-ky-thuat/main.pdf), entrypoint [main.tex](../bao-cao-ky-thuat/main.tex); 11 file chapter/front matter và 14 cặp nguồn `.drawio`/PDF trong thư mục báo cáo.
- Với `PYTHONUTF8=1`, chạy `python <latex-plugin>/scripts/compile_latex.py <report>/main.tex --compiler texlive --engine xelatex --output-directory <repo>/artifacts/report-build --json` → `BUILD_EXIT=0`. `pdfinfo artifacts/report-build/main.pdf` → `Pages: 51`, `Page size: 595.28 x 841.89 pts (A4)`. Render bằng `pdftoppm -r 100 -png artifacts/report-build/main.pdf artifacts/report-render-final2/page` → 51 trang.
- Kiểm tra XML `.drawio`, PDF tương ứng và cross-reference bằng Python: 14 sơ đồ, không thiếu file, không label trùng, không ref thiếu, 0 `tikzpicture` trong chapter; `git diff --check` exit 0. Bản 51 trang trước khi điền bìa có SHA-256 `C41BA131E70729204568388B7C3A2BC42C221FC6959EB07E751FF29A300504AA` và đã được review trực quan.
- Sau khi điền tên/MSSV: build XeLaTeX exit 0, `pdftotext -f 1 -l 1 -layout artifacts/report-build/main.pdf -` xác nhận năm cặp tên/MSSV; đã render và xem trực tiếp trang bìa. Bản khi đó có SHA-256 `F0589177CF4F7D24DCE87EB3FF5AE3123188DA6524CC7365CD6018E2E200B6B4`.
- Sau pull và gộp nội dung dashboard: build XeLaTeX exit 0; `pdfinfo artifacts/report-build/main.pdf` → 51 trang A4; render trang 40 và kiểm tra trực quan. PDF ở lượt đó có SHA-256 `E126C83045856662F859B4E206B6B4C4379AA3AF784C2ECF0437B6C2A2EC361C`.
- Sau bổ sung evidence Linh: `pdfinfo artifacts/report-build/main.pdf` → 52 trang A4; `pdftoppm -f <trang> -l <trang> -r 120 -png -singlefile artifacts/report-build/main.pdf <output>` render các trang 7–9, 42–45, 48–50 để review. `git diff --check` exit 0; 14 cặp draw.io/PDF còn đủ, không ref thiếu/label trùng. PDF mới có SHA-256 `F4AA8C02868483C6AF1E0D60147299DA74F564B26C37622F8CF1DCB91BA7ACF6`.
- Đã mở [BL-THANH-40](../backlog.md#nhân) cho Nhân về mô tả số Cassandra partition trên mỗi API request. Nội dung Linh/Trọng/Nhân/Mạnh còn cần owner review; không suy ra checkpoint nhóm DONE.
