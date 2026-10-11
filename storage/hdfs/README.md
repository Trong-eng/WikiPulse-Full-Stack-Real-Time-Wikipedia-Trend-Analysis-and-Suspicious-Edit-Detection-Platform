# HDFS — W2-TRONG-01 / W3-LINH-01

CP0 đã dùng local volume Parquet. HDFS chưa triển khai tuần1. Profile full cần NameNode/DataNode đơn (replication1), named volumes, healthcheck và Hadoop config trên Spark; DATA_BASE_PATH=hdfs://namenode:9000/wikipulse. Checkpoint HDFS cần URI riêng. Full profile chỉ nghiệm thu khi đọc lại Bronze/Silver/Gold và restart giữ dữ liệu. Kiểm tra ARM64 image trước khi chọn, không hardcode amd64 giả lập mà chưa test.
