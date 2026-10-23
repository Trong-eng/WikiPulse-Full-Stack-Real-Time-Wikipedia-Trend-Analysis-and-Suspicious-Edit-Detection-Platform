# WikiPulse — Tổng kết tuần 1

Kỳ báo cáo: tuần 1, tính từ 11/10/2026 (ngày lập kế hoạch checkpoint) · Chốt ngày 23/10/2026 · Mã nguồn: nhánh `main`, commit `541cf9b`, đã gộp phần việc của cả 5 thành viên.

## Tóm tắt

- **Tiến độ:** đạt mốc CP0, luồng dữ liệu chạy được từ đầu đến cuối. Phần việc tuần 1 của cả 5 thành viên đã hoàn thành và đã gộp vào nhánh chính.
- **Kết quả chính:** dữ liệu Wikipedia đi hết luồng xử lý và hiển thị được trên dashboard. Luồng sự kiện trực tiếp (LIVE) của Wikipedia đã được đo thực tế. Đặc tả giao tiếp cho tuần 2 đã được thống nhất.
- **Trọng tâm tuần 2 (CP2):** thu thập LIVE liên tục, phát hiện xu hướng và sửa đổi đáng ngờ, API và dashboard dùng dữ liệu thật, khởi động HDFS.

## 1. Kết quả tuần 1

Luồng dữ liệu: `nguồn sự kiện → Kafka → Spark → Cassandra → API → Dashboard`. Toàn bộ luồng đã chạy với dữ liệu phát lại (replay). Nguồn LIVE đã khảo sát, chưa nối vào luồng.

| Năng lực | Kiểm chứng |
|---|---|
| Chạy toàn hệ thống bằng Docker Compose, có bài kiểm tra tự động từ đầu đến cuối (smoke test) | Smoke test đạt ngày 11/10; chạy lại trên các máy Windows ngày 15/10 và 20/10, đều đạt |
| Phát lại dữ liệu mẫu vào Kafka | Kiểm thử tự động đạt. Báo lỗi bằng mã thoát 0/1/2/3, đúng thiết kế khi chạy thật |
| Khảo sát luồng LIVE trong 30 phút (ngày 15/10, toàn bộ các wiki) | Khoảng 29 sự kiện/giây, tức khoảng 3,4 GB/ngày nếu lưu nguyên. Server ngắt kết nối 2 lần (sau khoảng 11 và 15 phút). Khi nối lại từ đúng vị trí, 52.642 sự kiện không thiếu, không trùng |
| Spark làm sạch và kiểm tra dữ liệu, ẩn danh người sửa, đếm hoạt động theo phút | Kiểm thử Spark tăng từ 16 lên 26 trường hợp, đều đạt. Đã chạy thử với mẫu LIVE |
| Lưu vào Cassandra, API kiểm tra tình trạng hệ thống và API hoạt động theo wiki | Kiểm thử API đạt, trong đó 4 kiểm thử chạy trên Cassandra thật. Phát lại lần hai không làm sai số liệu |
| Dashboard 4 trang: Tổng quan và Trạng thái hệ thống dùng dữ liệu thật, 2 trang còn lại hiển thị "chưa triển khai" | Có ảnh chụp trang Tổng quan và Trạng thái hệ thống trên dữ liệu thật. Kiểm thử giao diện đạt |
| Đặc tả giao tiếp tuần 2 (xu hướng, sửa đổi đáng ngờ, chi tiết sự kiện) | Ba phần liên quan (Spark, API, dashboard) đã thống nhất |
| Quy trình làm việc chung: kế hoạch cho từng việc, danh sách việc tồn đọng (backlog) | Đã áp dụng cho các phần việc tuần 1 |

Toàn bộ kiểm thử đã chạy lại ngày 23/10 trên code đã gộp: 121 kiểm thử nhẹ (API, dashboard, thu thập, replay), 26 kiểm thử Spark và 4 kiểm thử trên Cassandra thật, tất cả đều đạt.

**Phát hiện quan trọng:**
- Dữ liệu LIVE khác dữ liệu mẫu ban đầu. Người sửa ẩn danh nay dùng tài khoản tạm thời, chiếm 11% số sự kiện của enwiki và viwiki, nên cách đếm "sửa đổi ẩn danh" hiện tại không bắt được ca nào. Lỗi đã tái hiện được và sẽ sửa ở tuần 2.
- Server có thể ngắt kết nối bất cứ lúc nào, nên bộ thu phải tự nối lại thì mới chạy LIVE liên tục được.

## 2. Đóng góp của từng thành viên

| Thành viên | Vai trò | Đầu ra tuần 1 |
|---|---|---|
| Trọng | Trưởng nhóm, hạ tầng và tích hợp | Khung dự án, Docker Compose, smoke test end-to-end, đặc tả v0.1; chạy kiểm tra toàn hệ thống đạt mốc CP0 |
| Thành | Thu thập dữ liệu (Kafka, replay) | Định dạng thông điệp Kafka dùng chung, công cụ replay có xử lý lỗi, mẫu dữ liệu LIVE đã ẩn danh, khảo sát LIVE, quy trình làm việc chung |
| Linh | Xử lý dữ liệu (Spark) | Thêm 10 trường hợp kiểm thử; chạy mẫu LIVE qua Spark; tái hiện 3 lỗi trong backlog (2 trên mẫu LIVE, 1 bằng dữ liệu tự tạo); tài liệu module |
| Nhân | Lưu trữ và API (Cassandra, FastAPI) | Kiểm tra dữ liệu trước khi ghi, công bố lỗi 503 trong đặc tả API, 4 kiểm thử trên Cassandra thật, đánh giá thiết kế khóa bảng, báo cáo kỹ thuật LaTeX, đặc tả tuần 2 v0.2 |
| Mạnh | Dashboard (Streamlit) | Tiếp quản 4 trang, chạy lại CP0 trên máy mình, ảnh chụp các trang, hướng dẫn chạy dashboard |

## 3. Mục tiêu tuần 2 (CP2)

**Mục tiêu:** hệ thống nhận dữ liệu LIVE, tính ra xu hướng và sửa đổi đáng ngờ, và hiển thị các kết quả đó trên dashboard qua API.

Kết quả mong đợi:
1. **Thu thập LIVE liên tục.** Xong khi có log bộ thu chạy ít nhất 20 phút và tự nối lại ít nhất một lần, dữ liệu vào Kafka cùng định dạng với dữ liệu replay, kèm kiểm thử nối lại.
2. **Phân tích.** Tính hoạt động theo cửa sổ 1 phút và 5 phút (trượt 1 phút), xử lý sự kiện trùng hoặc đến muộn, chấm điểm sửa đổi đáng ngờ, nhận diện đúng tài khoản ẩn danh tạm thời. Xong khi kết quả khớp bộ dữ liệu chuẩn đã tính sẵn.
3. **API và dashboard.** Ba API mới (xu hướng, sửa đổi đáng ngờ, chi tiết sự kiện) đọc dữ liệu thật; ghi lặp lại không nhân đôi dữ liệu; mọi lỗi trả về cùng một định dạng. Cả 4 trang dashboard có bộ lọc, trạng thái rỗng/lỗi và nhãn "tạm tính" cho số chưa chốt. Xong khi kiểm thử trên Cassandra thật đạt cho 3 API, và cả 4 trang có ảnh chụp kèm kiểm thử giao diện.
4. **HDFS.** Xong khi có log cấu hình HDFS khởi động thành công.

## 4. Cách chạy lại kết quả tuần 1 (Windows)

Đã chạy thử từng lệnh ngày 23/10/2026 trên commit `541cf9b`: Windows 11, PowerShell, Docker Desktop 29.8.1, Python 3.12. Gõ lệnh trong PowerShell, tại thư mục gốc của repo. Trên Windows chưa dùng được `make` ([BL-THANH-06](docs/backlog.md#trọng)); bước nào tương ứng với một target trong `Makefile` thì dùng đúng lệnh gốc của target đó. Cách ngắn hơn: sau khi đã có `.venv` (bước 4), chạy `powershell -ExecutionPolicy Bypass -File scripts\wikipulse.ps1 <target>` với cùng tên target như `make` (xem danh sách bằng target `help`). Tham số `-ExecutionPolicy Bypass` cần thiết vì Windows mặc định chặn chạy script `.ps1`. Nguồn chuẩn của lệnh chạy là [README.md](README.md); nếu README thay đổi thì làm theo README.

Cần có sẵn: Git, Python 3.11 hoặc 3.12, và Docker Desktop đang chạy (nên cấp 6–8 GB RAM cho Docker).

### 4.1. Chuẩn bị (chỉ làm một lần)

1. Tải mã nguồn về máy.
   ```powershell
   git clone https://github.com/Trong-eng/WikiPulse-Full-Stack-Real-Time-Wikipedia-Trend-Analysis-and-Suspicious-Edit-Detection-Platform.git
   ```
2. Vào thư mục repo. Mọi lệnh phía sau đều chạy từ đây.
   ```powershell
   cd WikiPulse-Full-Stack-Real-Time-Wikipedia-Trend-Analysis-and-Suspicious-Edit-Detection-Platform
   ```
3. Tạo file cấu hình `.env` từ file mẫu. File này gồm chế độ chạy (`PIPELINE_MODE=REPLAY`) và các cổng: API 18000, dashboard 8501, Kafka 19092. Nếu đã có `.env` thì bỏ qua bước này.
   ```powershell
   Copy-Item .env.example .env
   ```
4. Tạo môi trường Python riêng (`.venv`) để chạy test và script, không ảnh hưởng Python của máy.
   ```powershell
   python -m venv .venv
   ```
5. Cài thư viện của dự án, công cụ test và thư viện dashboard vào `.venv`. Mỗi khi kéo code mới mà `pyproject.toml` có thay đổi thì chạy lại bước này. Thiếu thư viện thì test Cassandra sẽ báo lỗi.
   ```powershell
   .venv\Scripts\python -m pip install -e ".[dev]" -r dashboard/requirements.txt
   ```

### 4.2. Chạy local (không cần Docker)

6. Chạy bộ kiểm thử nhẹ: API, dashboard, thu thập, replay. Bước này không cần Kafka, Cassandra hay Spark. Kết quả mong đợi: `121 passed`.
   ```powershell
   .venv\Scripts\python -m pytest -q -m "not integration and not spark"
   ```
7. Kiểm tra quy chuẩn code. Kết quả mong đợi: `All checks passed!`.
   ```powershell
   .venv\Scripts\ruff check .
   ```

### 4.3. Chạy toàn hệ thống bằng Docker

8. Kiểm tra file `docker-compose.yml` có hợp lệ không. Không in gì là hợp lệ.
   ```powershell
   docker compose config --quiet
   ```
9. Build image và khởi động hệ thống: Kafka, Cassandra, bước tạo topic/bảng, Spark, API, dashboard. Lần đầu mất vài phút để tải image. Lệnh kết thúc khi các service đã chạy nền.
   ```powershell
   docker compose up -d --build api spark dashboard
   ```
10. Xem trạng thái các service. Chờ đến khi `kafka`, `cassandra`, `api` và `dashboard` đều hiện `healthy`. Hai service `init-topics` và `init-cassandra` chạy xong rồi thoát, đó là bình thường.
    ```powershell
    docker compose ps
    ```
11. Gọi API kiểm tra tình trạng hệ thống. Kết quả mong đợi: `"status":"ok"` và `"cassandra":"ready"`.
    ```powershell
    curl.exe http://localhost:18000/health
    ```
12. Phát lại 11 sự kiện mẫu vào Kafka, sau đó Spark tự xử lý và ghi vào Cassandra. Kết quả mong đợi: dòng log `replay_complete events_published=11`.
    ```powershell
    docker compose run --rm replay
    ```
13. Đợi khoảng 30 giây cho Spark xử lý, rồi hỏi API số hoạt động của enwiki trong phút 00:00 ngày 01/01/2026 (thời gian của dữ liệu mẫu). Kết quả mong đợi: `event_count 5`, `edit_count 5`, `anonymous_edit_count 1`, `bot_edit_count 1`. Phát lại cùng dữ liệu trong khoảng watermark (10 phút) không làm tăng số này; giới hạn chi tiết xem README.
    ```powershell
    curl.exe "http://localhost:18000/api/v1/activity?wiki=enwiki&window=2026-01-01T00%3A00%3A00%2B00%3A00"
    ```
14. Mở dashboard trên trình duyệt để xem trang Tổng quan và Trạng thái hệ thống. Giao diện API (Swagger) ở `http://localhost:18000/docs`.
    ```powershell
    Start-Process http://localhost:8501
    ```
15. Xem 100 dòng log gần nhất của Spark khi cần kiểm tra lỗi. Thay `spark` bằng `api`, `kafka`... để xem log service khác.
    ```powershell
    docker compose logs --tail=100 spark
    ```
16. Chạy bộ kiểm thử Spark bên trong container, không cần cài Java trên máy. Kết quả mong đợi: `26 passed`.
    ```powershell
    docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q
    ```
17. Tắt hệ thống. Dữ liệu trong volume vẫn giữ cho lần chạy sau.
    ```powershell
    docker compose down
    ```

### 4.4. Kiểm thử trên Cassandra thật (không bắt buộc)

18. Bật một Cassandra tạm, tách khỏi hệ thống ở trên, ở cổng 19042. Cần chờ khoảng 1 phút để Cassandra sẵn sàng.
    ```powershell
    docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8
    ```
19. Kiểm tra Cassandra tạm đã sẵn sàng. Nếu báo lỗi kết nối thì đợi thêm khoảng 10 giây rồi chạy lại, đến khi lệnh in ra số phiên bản (`4.1.8`). Bộ test chỉ thử kết nối vài giây, nên chạy bước 22 khi Cassandra chưa sẵn sàng sẽ lỗi.
    ```powershell
    docker exec wikipulse-it cqlsh -e "SELECT release_version FROM system.local"
    ```
20. Cho bộ test biết địa chỉ Cassandra tạm. Biến `$env:` chỉ có hiệu lực trong cửa sổ PowerShell hiện tại; mở cửa sổ mới thì phải đặt lại, nếu không bước 22 sẽ ra `4 skipped` thay vì chạy thật.
    ```powershell
    $env:CASSANDRA_IT_HOST = "127.0.0.1"
    ```
21. Cho bộ test biết cổng Cassandra tạm (cũng chỉ có hiệu lực trong cửa sổ hiện tại).
    ```powershell
    $env:CASSANDRA_IT_PORT = "19042"
    ```
22. Chạy 4 kiểm thử ghi/đọc trên Cassandra thật. Mỗi lần chạy tự tạo keyspace riêng rồi xóa. Kết quả mong đợi: `4 passed`.
    ```powershell
    .venv\Scripts\python -m pytest -q -m integration api/tests
    ```
23. Xóa Cassandra tạm.
    ```powershell
    docker rm -f wikipulse-it
    ```

### 4.5. Kiểm thử end-to-end tự động (smoke test)

24. Bật chế độ UTF-8 cho Python trong cửa sổ PowerShell hiện tại. Nếu thiếu bước này, smoke test có thể lỗi mã hoá trên Windows ([BL-THANH-11](docs/backlog.md#trọng)).
    ```powershell
    $env:PYTHONUTF8 = "1"
    ```
25. Chạy smoke test. Script tự dựng một hệ thống riêng với volume riêng, phát dữ liệu mẫu, kiểm tra số liệu ở mọi tầng (Kafka, Parquet, Cassandra, API, dashboard), rồi tự dọn. Không đụng tới hệ thống ở mục 4.3. Mất vài phút. Kết quả mong đợi: `"status": "passed"`; bằng chứng lưu ở `artifacts\smoke-<thời gian>-<mã>\`.
    ```powershell
    .venv\Scripts\python scripts\smoke_test.py
    ```

## Phụ lục — nguồn chi tiết

- Kế hoạch 4 tuần và định nghĩa CP: [plans.md](plans.md)
- Trạng thái từng việc và bằng chứng: [docs/checkpoints.md](docs/checkpoints.md), plan từng việc trong [docs/plans/](docs/plans/)
- Đặc tả giao tiếp: [docs/contracts.md](docs/contracts.md) · Việc tồn đọng và quyết định chờ chốt: [docs/backlog.md](docs/backlog.md)
- Nghiệm thu CP0: [docs/trong/verification.md](docs/trong/verification.md) · Khảo sát LIVE: [docs/thanh/ingestion-spike.md](docs/thanh/ingestion-spike.md) · Báo cáo kỹ thuật: [docs/bao-cao-ky-thuat/](docs/bao-cao-ky-thuat/)

File này giữ nguyên sau khi gửi. Nếu cần sửa thì thêm mục "Đính chính" ở cuối.
