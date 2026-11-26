# Báo cáo kỹ thuật WikiPulse

Báo cáo tổng hợp bài toán, cơ sở lý thuyết, thiết kế, kết quả kiểm thử và giới hạn của hệ thống. Bản nộp là `main.pdf`.

## Slide thuyết trình

- [Slide PowerPoint](slide-wikipulse.pptx) gồm 12 slide; nội dung thuyết trình nằm trong Notes của từng slide.
- [Kịch bản thuyết trình](loi-thoai-slide.md) là bản đọc riêng, đồng bộ với Notes.
- Các sơ đồ ở slide 4, 5, 6 và 8 là ảnh xuất trực tiếp từ PDF sơ đồ trong `hinh/so-do/`; nguồn `.drawio` tương ứng vẫn nằm cùng thư mục. Để sửa nội dung sơ đồ, chỉnh file `.drawio` rồi xuất và thay ảnh trên slide. Ảnh dashboard là ảnh chụp thật.

## Biên dịch

Cần TeX Live hoặc MiKTeX với XeLaTeX, latexmk và BibTeX. Từ thư mục này chạy:

```bash
latexmk -xelatex main.tex
```

`main.tex` khai báo cấu hình và thứ tự nội dung; mỗi chapter nằm trong một file riêng ở `chapters/`. Sơ đồ có nguồn `.drawio` để chỉnh sửa và bản PDF cùng tên để nhúng vào báo cáo. Khi thay đổi sơ đồ, xuất lại PDF từ nguồn và kiểm tra trực quan sau khi biên dịch.

Trang bìa ghi mã học phần IT4043E và giảng viên Trần Việt Trung theo thông tin được cung cấp. Khi cập nhật nội dung, giữ rõ nguồn, điều kiện và giới hạn của từng kết quả; không xem nhãn trạng thái quản lý công việc là bằng chứng kiểm thử.
