# Báo cáo kỹ thuật WikiPulse

Báo cáo LaTeX cả nhóm viết dần trong 4 tuần, theo mẫu báo cáo của Trường CNTT&TT. Mục đích: thành viên đọc là hiểu project, và cuối kỳ không phải soạn báo cáo lại từ đầu.

## Biên dịch

Cần TeX Live hoặc MiKTeX (XeLaTeX, latexmk, BibTeX).

```bash
cd docs/bao-cao-ky-thuat
latexmk -xelatex main.tex      # ra main.pdf
latexmk -c                     # dọn file phụ
```

Không cài LaTeX thì mở thư mục này trên Overleaf (chọn compiler XeLaTeX).

`main.tex` là entrypoint và khai báo preamble; các chapter, glossary, front matter và phụ lục
nằm trong `chapters/`. Sửa nội dung ở file tương ứng và biên dịch từ thư mục báo cáo để giữ
đường dẫn, cross-reference và bibliography.

## Quy ước

- Phần chưa làm: chỉ đề mục + `\chualam`.
- Phần đã viết nhưng còn sửa ở tuần sau: thêm `\dukiensua{việc gì, tuần/ID việc}` ngay dưới.
- Thông tin còn thiếu: `\canbosung{...}`, hiện màu đỏ. Trang bìa: mỗi thành viên tự điền họ tên, MSSV của mình; trưởng nhóm điền học phần và giảng viên.
- Việc trong `docs/checkpoints.md` chuyển DONE thì owner cập nhật mục tương ứng **trong cùng PR**: thay `\chualam` bằng nội dung, số liệu và bằng chứng chạy lại được; thêm một dòng vào bảng "Lịch sử cập nhật báo cáo".
- Không ghi kết quả chưa đo. Contract vẫn định nghĩa ở `docs/contracts.md`; báo cáo chỉ giải thích.
- Ảnh chụp màn hình để trong `hinh/`. Sơ đồ lưu nguồn `.drawio` chỉnh sửa được và bản PDF vector
  xuất từ cùng nguồn trong `hinh/so-do/`; LaTeX nhúng PDF. Sau khi sửa sơ đồ trong draw.io,
  export lại PDF tương ứng và kiểm tra cả hình lẫn trang báo cáo sau khi biên dịch.
