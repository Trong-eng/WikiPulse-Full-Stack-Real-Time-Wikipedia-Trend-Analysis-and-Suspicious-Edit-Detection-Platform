"""Run Kafka → Bronze/Silver → provisional Cassandra and finalized activity Gold."""

import logging
import os
import signal
from threading import Event

from processing.spark.wikipulse.paths import PipelinePaths
from processing.spark.wikipulse.sinks import ActivityBatchWriter
from processing.spark.wikipulse.supervisor import (
    close_pipeline,
    publish_progress,
    supervise_queries,
)

LOGGER = logging.getLogger(__name__)


def create_spark(settings):
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.master(os.environ.get("SPARK_MASTER", "local[2]"))
        .appName(f"WikiPulse-CP0-{settings.run_id}")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", os.environ.get("SPARK_SHUFFLE_PARTITIONS", "2"))
        .getOrCreate()
    )


def ensure_directory(spark, path):
    """Create the empty Silver boundary with the same filesystem as its URI."""
    hadoop_path = spark._jvm.org.apache.hadoop.fs.Path(path)
    filesystem = hadoop_path.getFileSystem(spark._jsc.hadoopConfiguration())
    if not filesystem.exists(hadoop_path) and not filesystem.mkdirs(hadoop_path):
        raise OSError(f"Cannot create Silver directory {path}")
    if not filesystem.getFileStatus(hadoop_path).isDirectory():
        raise OSError(f"Silver path is not a directory: {path}")


def start_pipeline_queries(spark, settings, store, queries):
    from processing.spark.wikipulse.transformations import (
        SILVER_SCHEMA,
        activity_windows,
        bronze_rows,
        deduplicate_events,
        gold_rows,
        invalid_rows,
        normalize_events,
        parse_events,
    )

    paths = PipelinePaths.from_settings(settings)
    source = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.kafka_raw_topic)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "true")
        .option("maxOffsetsPerTrigger", settings.max_offsets_per_trigger)
        .load()
    )
    parsed = parse_events(source)

    def start_parquet(frame, name, path, partitions):
        query = (
            frame.writeStream.queryName(name).format("parquet").outputMode("append")
            .option("path", path).option("checkpointLocation", paths.checkpoint(name))
            .partitionBy(*partitions).trigger(processingTime=settings.trigger_interval).start()
        )
        queries.append(query)

    start_parquet(
        bronze_rows(parsed, settings.pipeline_version), "bronze_raw", paths.bronze_raw,
        ("event_date", "event_hour"),
    )
    start_parquet(
        invalid_rows(parsed), "bronze_invalid", paths.bronze_invalid, ("event_date", "event_hour"),
    )
    ensure_directory(spark, paths.silver)
    start_parquet(
        deduplicate_events(normalize_events(parsed, settings), settings.watermark_delay),
        "silver_events", paths.silver, ("event_date", "event_hour"),
    )
    # A persisted boundary prevents chained stateful operators in an Update query.
    # Explicit schema also permits startup while Silver has no event files yet.
    silver_source = spark.readStream.schema(SILVER_SCHEMA).format("parquet").load(paths.silver)
    activity = activity_windows(silver_source, settings.watermark_delay)
    queries.append(
        activity.writeStream.queryName("activity_cassandra").outputMode("update")
        .foreachBatch(ActivityBatchWriter(store).write_activity_batch)
        .option("checkpointLocation", paths.checkpoint("activity_cassandra"))
        .trigger(processingTime=settings.trigger_interval).start()
    )
    start_parquet(
        gold_rows(activity), "activity_gold", paths.gold_activity,
        ("metric_date", "metric_hour", "wiki"),
    )


def run_pipeline(
    settings, *, spark_factory=create_spark, store_factory=None,
    query_starter=start_pipeline_queries, shutdown=None, progress_path=None,
):
    """Own every resource, including queries started before a later startup failure."""
    if store_factory is None:
        from wikipulse_core.serving import CassandraActivityStore

        store_factory = CassandraActivityStore
    shutdown = shutdown if shutdown is not None else Event()
    spark = None
    store = None
    queries = []
    previous_signals = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_signals[signum] = signal.getsignal(signum)
            signal.signal(signum, lambda number, frame: shutdown.set())
        spark = spark_factory(settings)
        store = store_factory(settings)
        query_starter(spark, settings, store, queries)
        if progress_path:
            publish_progress(progress_path, queries)
        LOGGER.info("All %d CP0 streaming queries started", len(queries))
        supervise_queries(spark, queries, shutdown, progress_path)
    except KeyboardInterrupt:
        shutdown.set()
    finally:
        close_pipeline(queries, store, spark)
        for signum, previous in previous_signals.items():
            signal.signal(signum, previous)


def main():
    from wikipulse_core.config import Settings
    from wikipulse_core.logging import configure_logging

    configure_logging("spark")
    # Spark datetime values at the Python driver are UTC because the container and session are UTC.
    os.environ["TZ"] = "UTC"
    import time

    if hasattr(time, "tzset"):
        time.tzset()
    settings = Settings.from_env()
    run_pipeline(settings, progress_path=os.environ.get("SPARK_PROGRESS_PATH"))


if __name__ == "__main__":
    main()
