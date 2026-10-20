"""The concrete CP0 event contract, rather than Spark's window implementation."""

import hashlib
import json
from datetime import datetime, timezone
from importlib import import_module, util
from pathlib import Path
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


@pytest.mark.parametrize(
    ("meta_time", "epoch", "expected"),
    [
        ("2024-01-02T00:00:10.123+07:00", 0, datetime(2024, 1, 1, 17, 0, 10, 123000)),
        ("2024-01-01T12:00:10Z", 0, datetime(2024, 1, 1, 12, 0, 10)),
        ("not-a-date", 1704110410, datetime(2024, 1, 1, 12, 0, 10)),
        (None, 1704110410, datetime(2024, 1, 1, 12, 0, 10)),
    ],
)
def test_event_time_priority_fallback_and_utc_partitions(spark, meta_time, epoch, expected):
    """UTC quyết định event time và partition, không phải ngày của offset nguồn."""
    transform = transformations()
    payload = event(
        meta={"id": "utc-case", "dt": meta_time}, timestamp=epoch,
        ingested_at="2024-01-02T00:00:20.456+07:00",
    )
    row = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, [payload])), settings()
    ).first()
    assert row.event_time == expected
    assert row.event_date == expected.date()
    assert row.event_hour == expected.hour
    assert row.ingested_at == datetime(2024, 1, 1, 17, 0, 20, 456000)


def test_mixed_batch_quarantines_bad_rows_and_preserves_optional_fields(spark):
    """Một batch lỗi không làm mất các event hợp lệ có title hoặc page_id."""
    transform = transformations()
    payloads = [
        "{broken", "null", {}, event(wiki=None), event(title=None, page_id=None),
        event(page_id=None, revision=None, length=None, namespace=None,
              anon=None, user="FixtureEditor", bot=None, minor=None, ingested_at="bad"),
        event(title=None, page_id=11),
    ]
    parsed = transform.parse_events(kafka_rows(spark, payloads))
    assert transform.bronze_rows(parsed, "0.1.0").count() == 7
    errors = {
        row.kafka_offset: row.error_code
        for row in transform.invalid_rows(parsed).collect()
    }
    assert errors == {
        0: "INVALID_JSON", 1: "INVALID_JSON", 2: "MISSING_EVENT_TIME",
        3: "MISSING_WIKI", 4: "MISSING_PAGE",
    }
    rows = transform.normalize_events(parsed, settings()).orderBy("kafka_offset").collect()
    assert [row.kafka_offset for row in rows] == [5, 6]
    optional = rows[0].asDict()
    assert all(optional[field] is None for field in (
        "page_id", "revision_old", "revision_new", "length_old", "length_new",
        "byte_delta", "namespace",
    ))
    assert (optional["is_bot"], optional["is_minor"], optional["is_anonymous"]) == (
        False, False, False,
    )
    assert optional["ingested_at"] == datetime(2024, 1, 1, 12, 0, 25)
    assert rows[1].page_title is None and rows[1].page_id == 11


def test_blank_source_ids_and_equivalent_instants_have_same_fallback(spark):
    """ID fallback bỏ qua cách viết timezone, thời điểm ingest và offset Kafka."""
    transform = transformations()
    payloads = [
        event(meta={"dt": "2024-01-01T12:00:10Z"}),
        *[
            event(meta={"id": source_id, "dt": "2024-01-01T19:00:10+07:00"},
                  ingested_at="2024-01-02T00:00:00Z")
            for source_id in (None, "", "   ")
        ],
    ]
    rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, payloads)), settings()
    ).collect()
    assert len({row.event_id for row in rows}) == 1
    assert len(rows[0].event_id) == 64


def test_fallback_distinguishes_stable_event_fields_and_source_id_takes_priority(spark):
    """Các sự kiện khác nhau không bị dedup nhầm khi thiếu ID nguồn."""
    transform = transformations()
    base = event(meta={"dt": "2024-01-01T12:00:10Z"})
    variants = [
        base, dict(base, wiki="viwiki"), dict(base, page_id=11),
        dict(base, title="Other page"), dict(base, revision={"new": 92}),
        dict(base, meta={"dt": "2024-01-01T12:00:11Z"}),
        dict(base, type="new"), dict(base, id=124),
    ]
    rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, variants)), settings()
    ).collect()
    assert len({row.event_id for row in rows}) == len(variants)
    with_source_id = [
        dict(payload, meta={**payload["meta"], "id": "  authoritative-id  "})
        for payload in variants
    ]
    rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, with_source_id)), settings()
    ).collect()
    assert {row.event_id for row in rows} == {"authoritative-id"}


def test_salt_changes_only_user_identity_and_silver_roundtrips_parquet(spark, tmp_path):
    """Giữ nullable fields và schema qua ranh giới Parquet giữa dedup/aggregation."""
    transform = transformations()
    payload = event(page_id=None, length=None, revision=None, comment="Synthetic comment")
    parsed = transform.parse_events(kafka_rows(spark, [payload]))
    original = transform.normalize_events(parsed, settings())
    other_settings = settings()
    other_settings.user_hash_salt = "another-test-salt"
    changed = transform.normalize_events(parsed, other_settings).first()
    before = original.first()
    assert changed.user_hash != before.user_hash
    assert changed.event_id == before.event_id
    destination = str(tmp_path / "silver")
    original.write.partitionBy("event_date", "event_hour").parquet(destination)
    restored = spark.read.schema(transform.SILVER_SCHEMA).parquet(destination)
    assert not {"user", "comment", "raw_payload"} & set(restored.columns)
    after = restored.first()
    for field in (
        "event_id", "event_time", "event_date", "event_hour", "user_hash",
        "kafka_topic", "kafka_partition", "kafka_offset", "page_id", "revision_new", "byte_delta",
    ):
        assert after[field] == before[field]


def test_activity_boundary_isolates_wikis_and_matches_sink_schema(spark):
    """Window là [start, end); log/categorize không tăng edit, anonymous hay bot edits."""
    transform = transformations()
    payloads = [
        event(meta={"id": "a", "dt": "2024-01-01T12:00:59.999Z"}),
        event(meta={"id": "b", "dt": "2024-01-01T12:01:00Z"}),
        event(meta={"id": "c", "dt": "2024-01-01T12:00:30Z"}, wiki="viwiki"),
        event(meta={"id": "d", "dt": "2024-01-01T12:00:40Z"}, type="categorize", bot=True),
        event(meta={"id": "e", "dt": "2024-01-01T12:00:45Z"}, type="log", bot=True),
        event(meta={"id": "f", "dt": "2024-01-01T12:00:50Z"}, type="new", bot=True),
    ]
    silver = transform.normalize_events(transform.parse_events(kafka_rows(spark, payloads)), settings())
    activity = transform.activity_windows(silver, "10 minutes")
    assert {field.name: field.dataType.simpleString() for field in activity.schema} == {
        "wiki": "string", "window_start": "timestamp", "window_end": "timestamp",
        "event_count": "bigint", "edit_count": "bigint", "new_page_count": "bigint",
        "anonymous_edit_count": "bigint", "bot_edit_count": "bigint", "updated_at": "timestamp",
    }
    rows = {
        (row.wiki, row.window_start): (
            row.event_count, row.edit_count, row.new_page_count,
            row.anonymous_edit_count, row.bot_edit_count,
        )
        for row in activity.collect()
    }
    assert rows == {
        ("enwiki", datetime(2024, 1, 1, 12)): (4, 1, 1, 1, 0),
        ("viwiki", datetime(2024, 1, 1, 12)): (1, 1, 0, 1, 0),
        ("enwiki", datetime(2024, 1, 1, 12, 1)): (1, 1, 0, 1, 0),
    }


def test_live_sample_contract_and_report_pending_findings(spark):
    """Kiểm sample đã pseudonymize; báo cáo finding riêng, không assert hành vi sai."""
    transform = transformations()
    path = Path(__file__).resolve().parents[3] / "tests/fixtures/recentchange_live_sample.jsonl"
    payloads = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    parsed = transform.parse_events(kafka_rows(spark, payloads))
    bronze_count = transform.bronze_rows(parsed, "0.1.0").count()
    invalid = transform.invalid_rows(parsed).collect()
    silver = transform.normalize_events(parsed, settings())
    rows = silver.collect()
    expected = {
        item["meta"]["id"]: item for item in payloads
        if item.get("wiki") in ("enwiki", "viwiki") and item["meta"].get("domain") != "canary"
    }
    assert bronze_count == 11
    assert len(rows) == len(expected) == 9
    assert {row.event_id for row in rows} == set(expected)
    assert not {"user", "comment", "raw_payload"} & set(silver.columns)
    for row in rows:
        source = expected[row.event_id]
        assert row.page_id is None
        assert row.page_title == source["title"]
        assert row.event_time == datetime.fromisoformat(
            source["meta"]["dt"].replace("Z", "+00:00")
        ).replace(tzinfo=None)
        assert row.user_hash == hashlib.sha256(
            ("test-salt|" + source["user"]).encode("utf-8")
        ).hexdigest()
        if row.event_type in ("categorize", "log"):
            assert row.revision_new is None and row.byte_delta is None
        if row.event_type == "new":
            assert row.length_old is None and row.byte_delta is None
    # Không có business event hợp lệ bị đưa nhầm vào quarantine.
    canary_offsets = {
        index for index, item in enumerate(payloads) if item["meta"].get("domain") == "canary"
    }
    assert {row.kafka_offset for row in invalid} <= canary_offsets
    activity = transform.activity_windows(silver, "10 minutes").orderBy("wiki", "window_start")
    counts = {
        (row.wiki, row.window_start.strftime("%H:%M")): (
            row.event_count, row.edit_count, row.new_page_count, row.bot_edit_count,
        )
        for row in activity.collect()
    }
    # Expected độc lập, đếm tay từ 11 dòng fixture; anonymous chờ BL-THANH-19.
    assert counts == {
        ("enwiki", "10:13"): (4, 3, 0, 1), ("enwiki", "10:14"): (2, 2, 0, 0),
        ("enwiki", "10:15"): (1, 0, 0, 0), ("enwiki", "10:16"): (1, 0, 1, 0),
        ("viwiki", "10:14"): (1, 1, 0, 0),
    }
    temporary_edits = [
        row for row in rows
        if row.event_type == "edit" and expected[row.event_id]["user"].startswith("~")
    ]
    # Sample LIVE không có missing-user: tái hiện BL-THANH-21 bằng hai event tổng hợp.
    missing_user = event()
    missing_user.pop("user")
    null_user = event(meta={"id": "missing-user-2", "dt": "2024-01-01T12:00:11Z"}, user=None)
    missing_rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, [missing_user, null_user])), settings()
    ).collect()
    assert len(missing_rows) == 2
    print("LIVE_SAMPLE_REPORT=" + json.dumps({
        "bronze": bronze_count, "silver": len(rows), "invalid": len(invalid),
        "activity": [
            {"wiki": key[0], "window_utc_hhmm": key[1], "event_edit_new_bot": value}
            for key, value in sorted(counts.items())
        ],
        "BL-THANH-19": {
            "temporary_edits": len(temporary_edits),
            "recognized_anonymous": sum(row.is_anonymous for row in temporary_edits),
        },
        "BL-THANH-20": {"canary_quarantine_errors": [row.error_code for row in invalid]},
        "BL-THANH-21": {
            "synthetic_missing_user_rows": len(missing_rows),
            "nonnull_hashes": sum(row.user_hash is not None for row in missing_rows),
            "distinct_nonnull_hashes": len({
                row.user_hash for row in missing_rows if row.user_hash is not None
            }),
        },
    }, sort_keys=True))
