# HDFS — full stack và acceptance

Profile `full` chạy một NameNode và một DataNode, replication 1, volume `hdfs-name`/`hdfs-data` riêng theo Compose project. Image [Apache Hadoop 3.4.3](https://github.com/apache/hadoop/pkgs/container/hadoop) được pin manifest digest trong Compose, hỗ trợ ARM64/AMD64; đã chạy native ARM64. RPC 9000 và cổng DataNode chỉ dùng trong Docker network, không publish ra host. Topology demo không có HA/auth/Kerberos.

## Chạy full stack

Từ repo root, tạo `.env` theo `.env.example`, cài dependencies theo README gốc. Với W2 phải dùng `PIPELINE_VERSION=0.2.0`, **RUN_ID mới và namespace Cassandra mới** khi chuyển từ Silver v0.1 hoặc đổi storage/scoring. Không dùng lại checkpoint/run cũ.

```sh
COMPOSE_PROJECT_NAME=wikipulse-full RUN_ID=full-w2 CASSANDRA_KEYSPACE=wikipulse_full make up-full
COMPOSE_PROJECT_NAME=wikipulse-full RUN_ID=full-w2 CASSANDRA_KEYSPACE=wikipulse_full make replay
```

Chọn port khác trong `.env` nếu core/dev stack đang chiếm cổng. Các lệnh tương đương trên Windows/macOS/Linux (không cần Make):

```sh
docker compose -f docker-compose.yml -f docker-compose.hdfs.yml --profile full config --quiet
docker compose -f docker-compose.yml -f docker-compose.hdfs.yml --profile full up -d --build --wait --wait-timeout 240 api spark dashboard
docker compose run --rm replay
docker compose -f docker-compose.yml -f docker-compose.hdfs.yml --profile full ps
```

Với các lệnh trực tiếp, đặt cùng `COMPOSE_PROJECT_NAME`, `RUN_ID`, `CASSANDRA_KEYSPACE` và ports trong `.env`/shell cho mọi lệnh. `make down-full` (hoặc cùng Compose prefix + `down`) giữ volume. Không thêm `--volumes` trừ khi chủ động xóa đúng môi trường test.

Profile bật các HDFS services; overlay `docker-compose.hdfs.yml` chuyển **cả dữ liệu và checkpoints** của Spark sang HDFS và thêm dependency `init-hdfs`. Chỉ bật `--profile full` không tự đổi đường dữ liệu của Spark. Core `make up` mặc định dùng local volume và không chạy HDFS.

| Biến của full overlay | Mặc định | Ý nghĩa |
|---|---|---|
| `HDFS_BASE_PATH` | `hdfs://namenode:9000/wikipulse` | Ghi đè `DATA_BASE_PATH` của Spark |
| `HDFS_CHECKPOINT_PATH` | `hdfs://namenode:9000/checkpoints` | Ghi đè `SPARK_CHECKPOINT_PATH` của Spark |

Spark tự thêm `RUN_ID` và tên query vào các URI theo contract. Hadoop client config được mount read-only vào Spark; dùng DataNode hostname trong Compose network. HDFS chạy user root cùng Spark trong môi trường demo riêng, không thay quyền toàn filesystem bằng chmod 777.

## Readiness và restart

- NameNode phải trả RPC và thoát safe mode. DataNode kiểm tra qua IPC `-getDatanodeInfo`. Hai node không có dependency health vòng tròn.
- Compose không bảo đảm reverse DNS cho IP container, nên tắt `dfs.namenode.datanode.registration.ip-hostname-check` trong mạng demo riêng; DataNode vẫn dùng forward hostname `datanode`. Không áp dụng cấu hình này nguyên trạng cho cluster ngoài môi trường demo.
- `init-hdfs` chờ cả hai healthy và thử kiểm tra node đăng ký tối đa 30 lần (nghỉ 2 giây giữa các lần), tạo thư mục gốc rồi ghi/đọc một block thử và xóa probe; lỗi trả exit khác 0, chặn Spark startup.
- Spark probe đọc progress do supervisor xuất: đủ 9 query, tất cả active, timestamp UTC trong 60 giây. Progress cũ được xóa trước khi driver khởi động. Idle stream vẫn healthy vì supervisor tiếp tục cập nhật; healthy không có nghĩa dữ liệu nguồn luôn mới.
- NameNode chỉ format khi volume rỗng. Có dữ liệu nhưng thiếu `current/VERSION` thì startup fail để người vận hành kiểm tra; không tự format lại. Restart/recreate container dùng lại named volumes.

Lệnh chẩn đoán (giữ đúng project):

```sh
docker compose --profile full exec namenode hdfs dfsadmin -report
docker compose --profile full exec namenode hdfs dfsadmin -safemode get
docker compose exec spark python scripts/check_spark_ready.py
docker compose logs --tail=100 spark namenode datanode init-hdfs
```

Không cưỡng ép rời safe mode hoặc xóa checkpoints để chữa lỗi. Xem logs/node registration/volume trước; đổi schema/config phải tạo run mới. Tài liệu lệnh: [HDFS Commands Guide](https://hadoop.apache.org/docs/r3.4.3/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html).

## Nghiệm thu cô lập

```sh
make config-full
make smoke-full
make acceptance-hdfs
# Sau khi đã build image hiện tại:
.venv/bin/python scripts/smoke_test.py --hdfs --no-build
```

Smoke tự chọn project/run/port riêng và mặc định cleanup đúng volume của nó. `--keep` giữ lại để xem; lấy project và đường evidence từ `report.json`, dùng **cả hai file Compose và profile full** khi dọn. Mọi lỗi làm exit khác 0; `--no-build` chỉ dùng khi image đã chứa code mới.

`make smoke-full` kiểm API/dashboard, activity, Bronze/invalid/Silver/Gold và analytics Parquet. Sau khi dừng Spark, smoke recreate NameNode, DataNode, Kafka và Cassandra với volumes cũ. Nó đối chiếu offsets Kafka và đọc activity từ Cassandra qua API trước khi cho Spark chạy lại, rồi so ID đủ 9 query và đọc lại lake. Log và report nằm ở `artifacts/smoke-*/`.

`make acceptance-hdfs` dùng runner và fixture của Linh để kiểm tra late data, Gold finalized, retry activity và restart qua 7 phase có checkpoint chung. Hai lần chạy dùng project/volume test độc lập. Cách đọc evidence và giới hạn nghiệp vụ ở [W3-TRONG-01](../../docs/plans/W3-TRONG-01.md#kết-quả) và [W3-LINH-01](../../docs/plans/W3-LINH-01.md#kết-quả).
