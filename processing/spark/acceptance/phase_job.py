"""Drain the production queries for one isolated W3 fixture phase on real HDFS."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from wikipulse_core.config import Settings
from wikipulse_core.serving import CassandraActivityStore

from processing.spark.jobs.streaming_job import create_spark, start_pipeline_queries
from processing.spark.wikipulse.paths import PipelinePaths
from processing.spark.wikipulse.supervisor import close_pipeline

EXPECTED = Path(__file__).parents[1] / "tests/fixtures/week_three_expected.json"
MARKER = "W3_INJECTED_AFTER_ACTIVITY_UPSERT"


class FailAfterActivityWrite:
    """Fixture-only failure: database succeeds, streaming batch is not committed."""

    def __init__(self, store):
        self.store = store
        self.injected = False

    def upsert_activity(self, rows):
        rows = list(rows)  # Only this tiny, bounded acceptance fixture.
        self.store.upsert_activity(rows)
        if rows:
            self.injected = True
            raise RuntimeError(MARKER)

    def close(self):
        self.store.close()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def inspect(spark, paths, store, expected):
    """Independent literal expectations; never derive them from scoring code."""
    # A partitioned native sink may have only _spark_metadata before finalization.
    # Its empty output is valid, but cannot supply a schema by inference.
    schemas = {
        "gold_activity": "wiki string, window_start timestamp, window_end timestamp, "
                         "event_count long, edit_count long, new_page_count long, "
                         "anonymous_edit_count long, bot_edit_count long, updated_at timestamp, "
                         "metric_date date, metric_hour int",
        "gold_trends": "wiki string, page_key string, page_title string, namespace int, "
                       "window_start timestamp, window_end timestamp, edit_count long, "
                       "unique_editors long, abs_byte_delta long, trend_score double, "
                       "updated_at timestamp, metric_date date, metric_hour int",
    }
    frames = {}
    for name, path in {
        "bronze": paths.bronze_raw, "invalid": paths.bronze_invalid,
        "silver": paths.silver, "gold_activity": paths.gold_activity,
        "gold_trends": paths.gold_trends, "events": paths.event_details,
        "suspicious": paths.suspicious,
    }.items():
        reader = spark.read
        if name in schemas:
            reader = reader.schema(schemas[name])
        frames[name] = reader.parquet(path)
    counts = {name: frame.count() for name, frame in frames.items()}
    require(counts == expected["counts"], f"Layer counts: {counts} != {expected['counts']}")
    for name in ("silver", "events", "suspicious"):
        frame = frames[name]
        require(frame.select("event_id").distinct().count() == counts[name], f"Duplicate {name}")
        forbidden = {"user", "comment", "raw_payload"}
        if name != "silver":
            forbidden.add("user_hash")
        require(not forbidden & set(frame.columns), f"Privacy columns in {name}")
    ids = sorted(row.event_id for row in frames["silver"].select("event_id").collect())
    require(ids == expected["silver_ids"], f"Silver IDs: {ids}")
    require(frames["bronze"].select("kafka_topic", "kafka_partition", "kafka_offset")
            .distinct().count() == counts["bronze"], "Kafka offsets replayed into Bronze")
    require({r.error_code for r in frames["invalid"].select("error_code").collect()}
            == {"INVALID_JSON", "MISSING_PAGE"}, "Invalid/canary classification")

    partitions = {}
    for name in ("bronze", "invalid", "silver", "gold_activity", "gold_trends"):
        frame = frames[name].withColumn("_file", F.input_file_name())
        if name.startswith("gold"):
            day, hour, timestamp = "metric_date", "metric_hour", F.col("window_start")
        else:
            day, hour = "event_date", "event_hour"
            if name == "silver":
                timestamp = F.col("event_time")
            else:
                source = F.to_timestamp(F.get_json_object("raw_payload", "$.meta.dt"))
                timestamp = F.coalesce(source, F.col("kafka_timestamp"))
        bad = frame.filter((F.col(day) != F.to_date(timestamp)) | (F.col(hour) != F.hour(timestamp)))
        require(bad.count() == 0, f"Non-UTC partitions: {name}")
        parts = frame.select(day, hour, "_file", *(["wiki"] if name.startswith("gold") else []))
        seen = set()
        for row in parts.collect():
            require(f"/{day}={row[day]}/{hour}={row[hour]}/" in row._file,
                    f"Partition directories: {name}")
            if name.startswith("gold"):
                require(f"/wiki={row.wiki}/" in row._file, f"Wiki partition: {name}")
            seen.add(f"{row[day]}/{row[hour]}")
        partitions[name] = sorted(seen)

    start = datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc)
    activity = store.get_activity("enwiki", window=start)
    require(len(activity) == 1, "Activity must upsert one row per window")
    for key, value in expected["activity"].items():
        require(activity[0][key] == value, f"Activity {key}: {activity[0][key]} != {value}")
    latest = Window.partitionBy("wiki", "window_start", "page_key").orderBy(F.desc("batch_id"))
    trends = spark.read.parquet(paths.provisional_trends).withColumn("_rank", F.row_number().over(latest))
    target = "wiki = 'enwiki' AND window_start = TIMESTAMP '2026-01-01 23:59:00'"
    row = trends.filter(target + " AND _rank = 1 AND page_key = '10'").collect()
    require(len(row) == 1, "One provisional page key")
    for key, value in expected["trend"].items():
        require(abs(row[0][key] - value) < 1e-9, f"Trend {key}: {row[0][key]} != {value}")
    final = frames["gold_trends"].filter(target).collect()
    require(len(final) == int(expected["finalized"]), "Gold must wait for watermark")
    if expected["finalized"]:
        for key, value in expected["trend"].items():
            require(abs(final[0][key] - value) < 1e-9, f"Finalized trend {key}")
        gold = frames["gold_activity"].filter(target).collect()
        require(len(gold) == 1, "Finalized activity duplicated")
        for key, value in expected["activity"].items():
            require(gold[0][key] == value, f"Finalized activity {key}")
    for name, keys in (("gold_activity", ["wiki", "window_start"]),
                       ("gold_trends", ["wiki", "window_start", "page_key"])):
        require(frames[name].select(*keys).distinct().count() == counts[name], f"Duplicate {name}")
    return {"counts": counts, "silver_ids": ids, "partitions": partitions,
            "trend": {key: row[0][key] for key in expected["trend"]},
            "activity": {key: activity[0][key] for key in expected["activity"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("initial", "late", "retry_failure", "recovered",
                                         "finalized", "after_restart", "idle_restart"))
    args = parser.parse_args()
    settings = Settings.from_env()
    require(settings.run_id.startswith("w3-"), "Acceptance requires isolated w3- RUN_ID")
    require(settings.data_base_path.startswith("hdfs://"), "Must use real HDFS")
    require(settings.spark_checkpoint_path.startswith("hdfs://"), "Checkpoints must be HDFS")
    spark = create_spark(settings)
    spark.sparkContext.setLogLevel("WARN")
    store = CassandraActivityStore(settings)
    writer = FailAfterActivityWrite(store) if args.phase == "retry_failure" else store
    queries = []
    report = {"phase": args.phase, "run_id": settings.run_id}
    try:
        try:
            start_pipeline_queries(spark, settings, writer, queries)
            # Persisted Silver is a barrier: drain source queries before consumers,
            # then drain again for the no-data microbatch that advances watermark.
            for _ in range(2):
                for query in queries:
                    query.processAllAvailable()
        except Exception as exc:
            if args.phase != "retry_failure" or MARKER not in str(exc) or not writer.injected:
                raise
            report["injected_failure_observed"] = True
        else:
            require(args.phase != "retry_failure", "Failure injection was never exercised")
        report["query_ids"] = {q.name: str(q.id) for q in queries}
        report["query_run_ids"] = {q.name: str(q.runId) for q in queries}
        report["progress"] = {q.name: q.lastProgress for q in queries}
        require(len(queries) == 9, "All nine production queries must start")
        for query in reversed(queries):
            query.stop()
        if args.phase != "retry_failure":
            expected = json.loads(EXPECTED.read_text())[args.phase]
            report.update(inspect(spark, PipelinePaths.from_settings(settings), store, expected))
        report["status"] = "passed"
        print("W3_PHASE_REPORT=" + json.dumps(report, default=str, sort_keys=True), flush=True)
    finally:
        close_pipeline(queries, store, spark)


if __name__ == "__main__":
    main()
