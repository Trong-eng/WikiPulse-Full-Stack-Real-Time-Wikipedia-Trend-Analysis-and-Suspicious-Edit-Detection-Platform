"""So sánh analytics source tổng hợp với recording qua Spark thật."""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.spark


def test_recording_preserves_spark_analytics_for_valid_synthetic_events(tmp_path):
    from pyspark.sql import SparkSession
    from pyspark.sql.types import (
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    from ingestion.collector.app.recording import Recorder
    from processing.spark.wikipulse.analytics import score_events, trend_windows
    from processing.spark.wikipulse.scoring import ScoringConfig
    from processing.spark.wikipulse.transformations import normalize_events, parse_events
    from replay.replay_producer import run_replay

    spark = SparkSession.builder.master("local[1]").appName("recording-regression").getOrCreate()
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    spark.conf.set("spark.sql.shuffle.partitions", "1")
    settings = SimpleNamespace(pipeline_version="0.2.0", user_hash_salt="synthetic",
                               wiki_allowlist=("enwiki",))
    base = {"wiki": "enwiki", "title": "Example", "type": "edit", "namespace": 0,
            "timestamp": 1767225600, "length": {"old": 2000, "new": 0},
            "revision": {"old": 1, "new": 2}, "bot": False, "minor": False}
    source = [dict(base, meta={"id": f"event-{i}"}, user=user, comment=comment)
              for i, (user, comment) in enumerate([
                  ("~2026-123-4", "Reverted sensitive text"),
                  ("SyntheticEditor", "ordinary"), ("SyntheticEditor", "ordinary"),
                  (None, "ordinary"), ("~2026-123-5", "rollback private text"),
              ])]
    source[-1]["bot"] = True
    recorder = Recorder(tmp_path / "events.jsonl", tmp_path, secret=b"test")
    for event in source:
        recorder.write(recorder.prepare(json.dumps(event)))
    recorder.close()
    replayed = []
    with (tmp_path / "events.jsonl").open(encoding="utf-8") as recording:
        run_replay(recording, lambda key, payload: replayed.append(json.loads(payload)))
    schema = StructType([StructField("value", StringType()), StructField("topic", StringType()),
                         StructField("partition", IntegerType()), StructField("offset", LongType()),
                         StructField("timestamp", TimestampType())])

    def normalized(events):
        rows = [(json.dumps(event), "raw", 0, i, datetime(2026, 1, 1))
                for i, event in enumerate(events)]
        return normalize_events(parse_events(spark.createDataFrame(rows, schema)), settings)

    try:
        config = ScoringConfig({"edit_count": 0.4, "unique_editors": 0.3, "abs_byte_delta": 0.3},
                               {"edit_count": 100, "unique_editors": 100, "abs_byte_delta": 10000},
                               {"LARGE_DELETION": 30, "REVERT_PATTERN": 30, "ANONYMOUS_EDIT": 10},
                               1000, 100)
        results = []
        for events in (source, replayed):
            silver = normalized(events)
            scored = score_events(silver, config).orderBy("event_id").select(
                "event_id", "page_title", "is_anonymous", "is_revert", "risk_reasons", "risk_score"
            ).collect()
            trends = trend_windows(silver, "10 minutes", config).orderBy("window_start").select(
                "edit_count", "unique_editors", "abs_byte_delta", "trend_score"
            ).collect()
            results.append((scored, trends))
        assert results[0] == results[1]
    finally:
        spark.stop()
