FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 JAVA_HOME=/usr/lib/jvm/default-java SPARK_LOCAL_IP=127.0.0.1
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN pip install --no-cache-dir pyspark==3.5.6 cassandra-driver==3.29.2 pydantic==2.10.6 pytest==8.3.5
# Bake the Kafka connector into the image so startup does not depend on Maven availability.
RUN set -e; mkdir -p /opt/kafka-jars && cd /opt/kafka-jars && \
    for artifact in \
      org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.6/spark-sql-kafka-0-10_2.12-3.5.6.jar \
      org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.6/spark-token-provider-kafka-0-10_2.12-3.5.6.jar \
      org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar \
      org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar; \
    do curl --fail --location --retry 3 "https://repo.maven.apache.org/maven2/$artifact" -O; done
COPY . .
RUN pip install --no-cache-dir .
ENV PYTHONPATH=/workspace:/workspace/shared PYSPARK_SUBMIT_ARGS="--driver-memory 1g --conf spark.sql.shuffle.partitions=2 --jars /opt/kafka-jars/spark-sql-kafka-0-10_2.12-3.5.6.jar,/opt/kafka-jars/spark-token-provider-kafka-0-10_2.12-3.5.6.jar,/opt/kafka-jars/kafka-clients-3.4.1.jar,/opt/kafka-jars/commons-pool2-2.11.1.jar pyspark-shell"
CMD ["python", "-m", "processing.spark.jobs.streaming_job"]
