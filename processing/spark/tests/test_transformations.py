"""The concrete CP0 event contract, rather than Spark's window implementation."""

import hashlib
import json
from datetime import datetime, timezone
from importlib import import_module, util
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.spark


def transformations():
    module = "processing.spark.wikipulse.transformations"
    assert util.find_spec(module) is not None, "Missing event transformation implementation"
    return import_module(module)


def settings():
    return SimpleNamespace(
        pipeline_version="0.1.0", user_hash_salt="test-salt", wiki_allowlist=("enwiki", "viwiki")
    )


def event(**changes):
    result = {
        "meta": {"id": "source-event-1", "dt": "2024-01-01T12:00:10Z", "domain": "en.wikipedia.org"},
        "wiki": "enwiki",
        "id": 123,
        "page_id": 10,
        "title": "Example",
        "type": "edit",
        "namespace": 0,
        "revision": {"old": 90, "new": 91},
        "length": {"old": 250, "new": 230},
        "user": "192.0.2.1",
        "anon": True,
        "bot": False,
        "minor": True,
        "ingested_at": "2024-01-01T12:00:20Z",
    }
    result.update(changes)
    return result


def kafka_rows(spark, payloads):
    from pyspark.sql.types import (
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    schema = StructType(
        [
            StructField("value", StringType()),
            StructField("topic", StringType()),
            StructField("partition", IntegerType()),
            StructField("offset", LongType()),
            StructField("timestamp", TimestampType()),
        ]
    )
    rows = [
        (payload if isinstance(payload, str) else json.dumps(payload), "raw-topic", 1, i,
         datetime(2024, 1, 1, 12, 0, 25, tzinfo=timezone.utc))
        for i, payload in enumerate(payloads)
    ]
    return spark.createDataFrame(rows, schema)


def test_normalization_keeps_contract_and_pseudonymizes_user(spark):
    transform = transformations()
    parsed = transform.parse_events(kafka_rows(spark, [event()]))
    normalized = transform.normalize_events(parsed, settings())
    row = normalized.first().asDict()
    assert row["event_id"] == "source-event-1"
    assert row["event_time"] == datetime(2024, 1, 1, 12, 0, 10)
    assert row["ingested_at"] == datetime(2024, 1, 1, 12, 0, 20)
    assert row["byte_delta"] == -20
    assert row["revision_new"] == 91
    assert row["is_anonymous"] is True
    assert row["is_bot"] is False
    assert row["is_minor"] is True
    assert row["kafka_partition"] == 1
    assert row["user_hash"] == hashlib.sha256(b"test-salt|192.0.2.1").hexdigest()
    assert "user" not in row and "comment" not in row and "raw_payload" not in row
    # File readers allow nulls; inferred expression nullability is a Spark optimization.
    assert [(field.name, field.dataType) for field in normalized.schema] == [
        (field.name, field.dataType) for field in transform.SILVER_SCHEMA
    ]


def test_fallback_id_ignores_ingestion_and_kafka_metadata(spark):
    transform = transformations()
    payload = event(meta={"dt": "2024-01-01T12:00:10Z", "domain": "en.wikipedia.org"})
    newer_ingest = dict(payload, ingested_at="2024-01-01T12:04:20Z")
    changed_revision = dict(payload, revision={"old": 91, "new": 92})
    rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, [payload, newer_ingest, changed_revision])), settings()
    ).collect()
    assert len(rows[0].event_id) == 64
    assert rows[0].event_id == rows[1].event_id
    assert rows[0].event_id != rows[2].event_id


def test_invalid_payloads_quarantine_with_metadata(spark):
    transform = transformations()
    payloads = [
        "{malformed",
        event(meta={"id": "bad-time", "dt": "not-a-date"}),
        event(wiki=" "),
        event(title=" ", page_id=None),
    ]
    parsed = transform.parse_events(kafka_rows(spark, payloads))
    rows = transform.invalid_rows(parsed).orderBy("kafka_offset").collect()
    assert [row.error_code for row in rows] == [
        "INVALID_JSON", "MISSING_EVENT_TIME", "MISSING_WIKI", "MISSING_PAGE"
    ]
    assert rows[0].raw_payload == "{malformed"
    assert rows[0].kafka_topic == "raw-topic"
    assert rows[0].kafka_partition == 1
    assert rows[0].detected_at is not None
    assert transform.normalize_events(parsed, settings()).count() == 0


def test_canary_and_unconfigured_wiki_stay_bronze_but_leave_business(spark):
    transform = transformations()
    payloads = [
        event(),
        event(meta={"id": "canary-1", "domain": "canary", "dt": "2024-01-01T12:00:10Z"}),
        event(wiki="dewiki"),
    ]
    parsed = transform.parse_events(kafka_rows(spark, payloads))
    assert transform.bronze_rows(parsed, "0.1.0").count() == 3
    assert transform.invalid_rows(parsed).count() == 0
    assert transform.normalize_events(parsed, settings()).count() == 1


def test_epoch_time_fallback_and_optional_fields(spark):
    transform = transformations()
    payload = event(meta={"id": "epoch", "domain": "en.wikipedia.org"}, timestamp=1704110410)
    payload.pop("length")
    payload.pop("anon")
    normalized = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, [payload])), settings()
    ).first()
    assert normalized.event_time == datetime(2024, 1, 1, 12, 0, 10)
    assert normalized.byte_delta is None
    assert normalized.is_anonymous is True


def test_activity_counts_only_anonymous_and_bot_edits(spark):
    transform = transformations()
    payloads = [
        event(),
        event(meta={"id": "bot", "dt": "2024-01-01T12:00:30Z"}, bot=True, anon=False),
        event(meta={"id": "new", "dt": "2024-01-01T12:00:45Z"}, type="new", bot=True),
        event(meta={"id": "log", "dt": "2024-01-01T12:00:50Z"}, type="log"),
        event(meta={"id": "next", "dt": "2024-01-01T12:01:00Z"}),
    ]
    silver = transform.normalize_events(transform.parse_events(kafka_rows(spark, payloads)), settings())
    rows = transform.activity_windows(silver, "10 minutes").orderBy("window_start").collect()
    assert len(rows) == 2
    first = rows[0].asDict()
    assert first["window_start"] == datetime(2024, 1, 1, 12, 0)
    assert first["window_end"] == datetime(2024, 1, 1, 12, 1)
    assert [first[field] for field in (
        "event_count", "edit_count", "new_page_count", "anonymous_edit_count", "bot_edit_count"
    )] == [4, 2, 1, 1, 1]
    assert rows[1].event_count == 1


def test_duplicate_in_later_microbatch_and_restart_does_not_add_silver_row(spark, tmp_path):
    transform = transformations()
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "silver"
    checkpoint = tmp_path / "checkpoint"
    raw = kafka_rows(spark, [event()])
    source_schema = raw.schema

    def append_source(name, payload):
        (source / name).write_text(json.dumps({
            "value": json.dumps(payload), "topic": "raw-topic", "partition": 0,
            "offset": 1, "timestamp": "2024-01-01T12:00:25Z"
        }) + "\n")

    def process_available():
        source_df = spark.readStream.schema(source_schema).json(str(source))
        silver = transform.deduplicate_events(
            transform.normalize_events(transform.parse_events(source_df), settings()), "10 minutes"
        )
        query = (
            silver.writeStream.format("parquet").outputMode("append")
            .option("checkpointLocation", str(checkpoint)).trigger(availableNow=True)
            .start(str(output))
        )
        assert query.awaitTermination(60), "Bounded Silver query did not finish"

    append_source("first.json", event())
    process_available()
    append_source("duplicate.json", event(
        meta={"id": "source-event-1", "dt": "2024-01-01T12:00:11Z"}
    ))
    process_available()
    assert spark.read.schema(transform.SILVER_SCHEMA).parquet(str(output)).count() == 1


def test_gold_emits_old_window_only_after_silver_advances_watermark(spark, tmp_path):
    from pyspark.sql import functions as F

    transform = transformations()
    source = tmp_path / "silver"
    source.mkdir()
    output = tmp_path / "gold"
    checkpoint = tmp_path / "gold-checkpoint"

    def append_events(payloads):
        transform.normalize_events(
            transform.parse_events(kafka_rows(spark, payloads)), settings()
        ).write.mode("append").partitionBy("event_date", "event_hour").parquet(str(source))

    def process_available():
        silver = spark.readStream.schema(transform.SILVER_SCHEMA).parquet(str(source))
        gold = transform.gold_rows(transform.activity_windows(silver, "10 minutes"))
        query = (
            gold.writeStream.format("parquet").outputMode("append")
            .option("checkpointLocation", str(checkpoint))
            .partitionBy("metric_date", "metric_hour", "wiki").trigger(availableNow=True)
            .start(str(output))
        )
        assert query.awaitTermination(60), "Bounded Gold query did not finish"

    append_events([event()])
    process_available()
    assert not list(output.rglob("*.parquet")), "Gold must remain empty before finalization"
    append_events([event(meta={"id": "advance", "dt": "2024-01-01T12:12:01Z"})])
    process_available()
    rows = spark.read.parquet(str(output)).filter(
        F.col("window_start") == F.lit(datetime(2024, 1, 1, 12))
    ).collect()
    assert len(rows) == 1
    assert rows[0].event_count == 1
    assert rows[0].edit_count == 1
    assert rows[0].wiki == "enwiki"
