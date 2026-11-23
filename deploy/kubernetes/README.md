# Kubernetes skeleton — W3-TRONG-01

Skeleton phục vụ API activity và dashboard trong namespace `wikipulse`, dùng Cassandra có sẵn và hai Service ClusterIP. Bộ kiểm thử full stack dùng [Docker Compose + HDFS](../../storage/hdfs/README.md). Collector là Deployment có `replicas: 0` vì entrypoint LIVE hiện thoát mã 2. Collector chỉ kết nối ra ngoài nên không cần Service.

## Chuẩn bị

- Cấp một endpoint Cassandra mà Pod truy cập được. Đặt `CASSANDRA_HOST`, `CASSANDRA_PORT` và `CASSANDRA_KEYSPACE` trong `applications.yaml`. Giá trị `cassandra` mặc định cần Service cùng namespace. Dùng cùng keyspace với Spark nếu muốn dashboard hiển thị kết quả của pipeline đang chạy.
- Build hai image bằng `docker compose build api dashboard`. Với kind, nạp image vào cluster bằng `kind load docker-image wikipulse-api:0.1.0 wikipulse-dashboard:0.1.0`. Với cluster khác, publish qua registry của nhóm rồi đặt image/tag tương ứng trong Deployment và Job.

## Render và chạy thử

`kubectl kustomize deploy/kubernetes` render tại chỗ và không cần kết nối cluster. Các lệnh sau dành cho một cluster thử nghiệm đã được cấu hình, từ root của repo:

```sh
kubectl apply -k deploy/kubernetes
kubectl apply -f deploy/kubernetes/jobs/init-cassandra.yaml
kubectl -n wikipulse wait --for=condition=complete job/init-cassandra --timeout=310s
kubectl -n wikipulse rollout status deployment/api --timeout=120s
kubectl -n wikipulse rollout status deployment/dashboard --timeout=120s
kubectl -n wikipulse port-forward svc/dashboard 8501:8501
```

Job dùng image API và gọi initializer idempotent `python -m api.app.init_db` để tạo schema activity. Nếu cần chạy lại Job trên cluster thử nghiệm, xóa Job cũ rồi apply lại manifest Job. Khi đổi ConfigMap, apply và restart Deployment sử dụng biến môi trường để Pod đọc config mới.

Readiness API dùng `/health` để đưa Pod ra khỏi Service khi Cassandra lỗi. Liveness API kiểm tra cổng HTTP để tránh restart chỉ vì dependency lỗi. Dashboard dùng `/_stcore/health` cho tiến trình Streamlit và hiển thị trạng thái API ở trang System Status. Mở dashboard tại `http://127.0.0.1:8501` sau port-forward. Tham khảo [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/).

Phạm vi skeleton là ứng dụng stateless trong môi trường thử nghiệm. Kafka, Spark, HDFS, Cassandra, PVC, Ingress, TLS và Secret dành cho cấu hình cluster riêng.
