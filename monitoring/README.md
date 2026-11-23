# Monitoring WikiPulse

Overlay Compose theo dõi hai endpoint nội bộ bằng Prometheus và Blackbox Exporter. Mỗi 15 giây, exporter dùng HTTP GET và yêu cầu phản hồi `200` từ API `/health` và dashboard `/_stcore/health`.

| Probe | Cho biết |
| --- | --- |
| `api` | API truy cập được và báo Cassandra ready |
| `dashboard` | Máy chủ Streamlit phản hồi |

Từ repo root, chạy dưới cùng Compose project với WikiPulse. Với HDFS, thêm `-f docker-compose.hdfs.yml` và `--profile full` trước khi chỉ định lệnh `up` nếu muốn ghép toàn bộ cấu hình. Hai container monitoring có thể khởi động riêng. Khi API hoặc dashboard chưa chạy, probe của service đó trả `0`.

```sh
docker compose -f docker-compose.yml -f monitoring/compose.yml --profile monitoring \
  up -d prometheus blackbox
```

Mở [Prometheus](http://127.0.0.1:19090) rồi chạy các truy vấn dưới đây. Prometheus chỉ lắng nghe từ host qua loopback. Blackbox Exporter dùng mạng Compose nội bộ và không publish port. Volume `prometheus-data` giữ số liệu qua restart trong cửa sổ lưu trữ 2 ngày.

```promql
probe_success{job="wikipulse-readiness"}
probe_http_status_code{job="wikipulse-readiness"}
probe_duration_seconds{job="wikipulse-readiness"}
up{job="blackbox"}
```

`probe_success=1` nghĩa là probe nhận HTTP `200`. `probe_success=0` nghĩa là probe chạy nhưng request thất bại. Khi Prometheus không scrape được exporter, xem `up{job="blackbox"}` và `up{job="wikipulse-readiness"}` để phân biệt thiếu mẫu với target báo lỗi. Probe duration đo thời gian request health, còn độ trễ dữ liệu, Spark progress, Kafka lag và kết quả từng trang cần kiểm tra qua công cụ của module. Tham khảo [cấu hình multi-target exporter](https://prometheus.io/docs/guides/multi-target-exporter/) và [ví dụ Grafana](grafana/README.md).

Kiểm chứng cấu hình từ repo root trước khi khởi động services.

```sh
docker compose -f docker-compose.yml -f monitoring/compose.yml --profile monitoring config --quiet
docker compose -f docker-compose.yml -f monitoring/compose.yml --profile monitoring \
  run --rm --no-deps --entrypoint /bin/promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose -f docker-compose.yml -f monitoring/compose.yml --profile monitoring \
  run --rm --no-deps blackbox --config.file=/etc/blackbox_exporter/config.yml --config.check
```

Để dừng hai service, dùng lại cùng Compose project và overlay.

```sh
docker compose -f docker-compose.yml -f monitoring/compose.yml --profile monitoring \
  stop prometheus blackbox
```
