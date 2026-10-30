"""Independent analytics checkpoints downstream of persisted, deduplicated Silver."""

from processing.spark.wikipulse.paths import PipelinePaths
from processing.spark.wikipulse.sinks import AnalyticsBatchWriter, TrendChangelogWriter


def validate_sink(mode, store):
    if mode not in {"parquet", "cassandra"}:
        raise ValueError("SPARK_ANALYTICS_SINK must be parquet or cassandra")
    if mode == "cassandra":
        return AnalyticsBatchWriter(store)
    return None


def start_analytics_queries(silver, settings, queries, *, config, mode="parquet", store=None):
    from pyspark.sql import functions as F

    from processing.spark.wikipulse.analytics import (
        event_details,
        score_events,
        suspicious_edits,
        trend_windows,
    )

    writer = validate_sink(mode, store)
    paths = PipelinePaths.from_settings(settings)
    trends = trend_windows(silver, settings.watermark_delay, config)
    scored = score_events(silver, config)

    def builder(frame, name, output_mode):
        return (frame.writeStream.queryName(name).outputMode(output_mode)
                .option("checkpointLocation", paths.checkpoint(name))
                .trigger(processingTime=settings.trigger_interval))

    if writer is None:
        queries.append(builder(trends, "trends_provisional_parquet", "update")
                       .foreachBatch(TrendChangelogWriter(paths.provisional_trends).write_batch)
                       .start())
        queries.append(builder(suspicious_edits(scored), "suspicious_parquet", "append")
                       .format("parquet").option("path", paths.suspicious).start())
        queries.append(builder(event_details(scored), "events_parquet", "append")
                       .format("parquet").option("path", paths.event_details).start())
    else:
        for frame, name, output_mode, callback in (
            (trends, "trends_cassandra", "update", writer.write_trends_batch),
            (suspicious_edits(scored), "suspicious_cassandra", "append",
             writer.write_suspicious_batch),
            (event_details(scored), "events_cassandra", "append", writer.write_events_batch),
        ):
            queries.append(builder(frame, name, output_mode).foreachBatch(callback).start())
    finalized = trends.withColumn("metric_date", F.to_date("window_start")).withColumn(
        "metric_hour", F.hour("window_start")
    )
    queries.append(builder(finalized, "trends_gold", "append").format("parquet")
                   .option("path", paths.gold_trends)
                   .partitionBy("metric_date", "metric_hour", "wiki").start())
