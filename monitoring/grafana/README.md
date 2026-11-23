# Ví dụ truy vấn Grafana

Dùng Prometheus của [monitoring overlay](../README.md) làm data source. Nếu chạy Grafana trong cùng mạng Compose, địa chỉ datasource là `http://prometheus:9090`. Nếu Grafana là tiến trình chạy trực tiếp trên máy Docker, dùng `http://127.0.0.1:19090`.

- **Stat theo service:** `probe_success{job="wikipulse-readiness"}`. Legend `{{service}}`, ánh xạ `1` thành ready và `0` thành failed. Dùng trạng thái no data mặc định để nhận biết scrape chưa có kết quả.
- **Time series:** `probe_duration_seconds{job="wikipulse-readiness"}`. Legend `{{service}}`, đơn vị giây.

Grafana và alerting là phần cấu hình đội vận hành bổ sung khi cần. Các probe hiện tại quan sát readiness theo bảng trong [monitoring README](../README.md).
