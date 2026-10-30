"""Golden contract v0.2; expected values are hand-counted, not derived from Spark."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from processing.spark.tests.test_transformations import event, kafka_rows, settings, transformations

pytestmark = pytest.mark.spark
FIXTURES = Path(__file__).parent / "fixtures"


def analytics():
    from processing.spark.wikipulse import analytics
    return analytics


def config():
    from processing.spark.wikipulse.scoring import load_scoring
    return load_scoring()


def sample(spark):
    transform = transformations()
    lines = (FIXTURES / "week_two.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = transform.parse_events(kafka_rows(spark, lines))
    return parsed, transform.normalize_events(parsed, settings())


def test_silver_v02_and_golden_risk_detail(spark):
    transform = transformations()
    parsed, silver = sample(spark)
    expected = json.loads((FIXTURES / "week_two_expected.json").read_text())
    assert transform.bronze_rows(parsed, "0.2.0").count() == 8
    assert transform.invalid_rows(parsed).count() == 0
    rows = {row.event_id: row for row in silver.collect()}
    assert len(rows) == expected["silver_count"]
    assert rows["w2-b"].is_anonymous and rows["w2-b"].is_revert
    assert rows["w2-c"].user_hash is None and rows["w2-g"].user_hash is None
    scored = analytics().score_events(silver, config())
    detail = analytics().event_details(scored)
    assert not {"user", "user_hash", "comment", "raw_payload"} & set(detail.columns)
    assert set(detail.columns) == {
        "event_id", "wiki", "event_time", "page_key", "page_title", "namespace", "event_type",
        "revision_old", "revision_new", "length_old", "length_new", "byte_delta",
        "is_anonymous", "is_bot", "is_minor", "risk_score", "risk_reasons",
        "pipeline_version", "processed_at",
    }
    for row in detail.collect():
        wanted = expected["risk"][row.event_id]
        assert row.risk_score == wanted["score"]
        assert row.risk_reasons == wanted["reasons"]
    suspicious = analytics().suspicious_edits(scored)
    assert {row.event_id for row in suspicious.collect()} == {"w2-b", "w2-d"}
    assert "user_hash" not in suspicious.columns
    assert suspicious.schema["risk_score"].dataType.simpleString() == "int"
    for row in suspicious.collect():
        assert row.bucket_start == datetime(2026, 1, 1, 0, 1)


def test_golden_trends_sliding_windows_nulls_and_schema(spark):
    _, silver = sample(spark)
    expected = json.loads((FIXTURES / "week_two_expected.json").read_text())
    trends = analytics().trend_windows(silver, "10 minutes", config())
    target = trends.filter("window_start = TIMESTAMP '2026-01-01 00:00:00'")
    rows = {(row.wiki, row.page_key): row for row in target.collect()}
    assert len(rows) == 3
    for wanted in expected["trends"]:
        row = rows[(wanted["wiki"], wanted["page_key"])].asDict()
        for name, value in wanted.items():
            assert row[name] == (pytest.approx(value) if name == "trend_score" else value)
        assert row["window_end"] == datetime(2026, 1, 1, 0, 5)
    assert {field.name: field.dataType.simpleString() for field in trends.schema} == {
        "wiki":"string", "page_key":"string", "page_title":"string", "namespace":"int",
        "window_start":"timestamp", "window_end":"timestamp", "edit_count":"bigint",
        "unique_editors":"bigint", "abs_byte_delta":"bigint", "trend_score":"double",
        "updated_at":"timestamp",
    }
    # A single edit belongs to exactly five half-open windows, including across midnight.
    one = silver.filter("event_id = 'w2-a'")
    single = analytics().trend_windows(one, "10 minutes", config()).collect()
    assert len(single) == 5
    assert {r.window_start for r in single} == {
        datetime(2025, 12, 31, 23, minute) for minute in (56, 57, 58, 59)
    } | {datetime(2026, 1, 1)}


@pytest.mark.parametrize("comment,wanted", [
    (None, False), ("", False), ("Discuss reverting tomorrow", False),
    ("Revert", True), ("  REVERTED edit", True), ("Undid revision 42", True),
    ("Undo revision 42", True), ("Rolled back edits", True), ("Rollback edit", True),
    ("Reverting edit", True), ("Reversion discussion", False),
])
def test_revert_patterns_are_anchored_and_privacy_safe(spark, comment, wanted):
    transform = transformations()
    parsed = transform.parse_events(kafka_rows(spark, [event(comment=comment)]))
    normalized = transform.normalize_events(parsed, settings())
    assert normalized.first().is_revert is wanted
    assert "comment" not in normalized.columns


def test_risk_threshold_null_bot_and_max_score(spark):
    transform = transformations()
    payloads = [event(length={"old":1000, "new":501}, anon=False),
                event(length={"old":1000, "new":500}, anon=False),
                event(length=None, anon=False),
                event(length=None, anon=True, bot=True)]
    silver = transform.normalize_events(transform.parse_events(kafka_rows(spark, payloads)), settings())
    scored = analytics().score_events(silver, config()).orderBy("kafka_offset").collect()
    assert [row.risk_score for row in scored] == [0, 30, 0, 0]
    from dataclasses import replace
    capped = replace(config(), max_score=15)
    assert [row.risk_score for row in analytics().score_events(silver, capped)
            .orderBy("kafka_offset").collect()] == [0, 15, 0, 0]


def test_temporary_account_overrides_false_anon_and_blank_user_is_null(spark):
    transform = transformations()
    payloads = [event(user="~2026-12345-678", anon=False), event(user=""), event(user="   ")]
    rows = transform.normalize_events(
        transform.parse_events(kafka_rows(spark, payloads)), settings()
    ).orderBy("kafka_offset").collect()
    assert rows[0].is_anonymous is True
    assert rows[1].user_hash is None and rows[2].user_hash is None


def test_trend_caps_and_latest_metadata_do_not_split_page_keys(spark):
    from dataclasses import replace
    transform = transformations()
    payloads = [
        event(meta={"id":"first", "dt":"2026-01-01T00:00:00Z"}, title="Old", namespace=0),
        event(meta={"id":"last", "dt":"2026-01-01T00:01:00Z"}, title="New", namespace=1),
    ]
    silver = transform.normalize_events(transform.parse_events(kafka_rows(spark, payloads)), settings())
    capped = replace(config(), normalization_caps={
        "edit_count":1, "unique_editors":1, "abs_byte_delta":1,
    })
    rows = analytics().trend_windows(silver, "10 minutes", capped).filter(
        "window_start = TIMESTAMP '2026-01-01 00:00:00'"
    ).collect()
    assert len(rows) == 1
    assert (rows[0].page_key, rows[0].page_title, rows[0].namespace) == ("10", "New", 1)
    assert rows[0].trend_score == 1.0


def test_streaming_trends_late_data_restart_and_finalized_gold(spark, tmp_path):
    """Real state store: late-but-open updates; too-late events cannot reopen final windows."""
    from processing.spark.wikipulse.sinks import TrendChangelogWriter

    transform = transformations()
    source = tmp_path / "silver"
    source.mkdir()
    snapshots = tmp_path / "updates"
    gold = tmp_path / "gold"

    def publish(identifier, timestamp):
        payload = event(meta={"id":identifier, "dt":timestamp}, user=identifier)
        transform.normalize_events(transform.parse_events(kafka_rows(spark, [payload])), settings())\
            .write.mode("append").parquet(str(source))

    def process():
        silver = spark.readStream.schema(transform.SILVER_SCHEMA).parquet(str(source))
        trends = analytics().trend_windows(silver, "10 minutes", config())
        update = (trends.writeStream.outputMode("update")
                  .foreachBatch(TrendChangelogWriter(str(snapshots)).write_batch)
                  .option("checkpointLocation", str(tmp_path / "update-checkpoint"))
                  .trigger(availableNow=True).start())
        try:
            assert update.awaitTermination(90)
        finally:
            update.stop()
        finalized = (trends.writeStream.outputMode("append").format("parquet")
                     .option("checkpointLocation", str(tmp_path / "gold-checkpoint"))
                     .trigger(availableNow=True).start(str(gold)))
        try:
            assert finalized.awaitTermination(90)
        finally:
            finalized.stop()

    def latest():
        return spark.read.parquet(str(snapshots)).filter(
            "window_start = TIMESTAMP '2026-01-01 00:00:00'"
        ).orderBy("batch_id", ascending=False).first()

    publish("a", "2026-01-01T00:04:30Z")
    process()
    assert latest().edit_count == 1
    # File sinks may create empty Parquet files for empty output batches.
    assert spark.read.parquet(str(gold)).count() == 0
    publish("late-open", "2026-01-01T00:01:00Z")
    process()  # Restarts both queries with their checkpoints.
    assert latest().edit_count == 2
    publish("advance", "2026-01-01T00:16:00Z")
    process()
    target = spark.read.parquet(str(gold)).filter(
        "window_start = TIMESTAMP '2026-01-01 00:00:00'"
    ).collect()
    assert len(target) == 1 and target[0].edit_count == 2
    assert target[0].trend_score == pytest.approx(latest().trend_score)
    publish("too-late", "2026-01-01T00:02:00Z")
    process()
    assert latest().edit_count == 2
    final = spark.read.parquet(str(gold)).filter(
        "window_start = TIMESTAMP '2026-01-01 00:00:00'"
    ).collect()
    assert len(final) == 1 and final[0].edit_count == 2


def test_analytics_query_wiring_produces_all_four_outputs(spark, tmp_path):
    from types import SimpleNamespace

    from processing.spark.wikipulse.analytics_queries import start_analytics_queries
    from processing.spark.wikipulse.paths import PipelinePaths

    source = tmp_path / "silver-input"
    _, initial = sample(spark)
    initial.write.parquet(str(source))
    runtime = SimpleNamespace(data_base_path=str(tmp_path / "data"),
                              spark_checkpoint_path=str(tmp_path / "checkpoints"),
                              run_id="w2", watermark_delay="10 minutes",
                              trigger_interval="1 second")
    paths = PipelinePaths.from_settings(runtime)
    transform = transformations()
    silver = spark.readStream.schema(transform.SILVER_SCHEMA).parquet(str(source))
    queries = []
    try:
        start_analytics_queries(silver, runtime, queries, config=config())
        assert {q.name for q in queries} == {
            "trends_provisional_parquet", "trends_gold", "suspicious_parquet", "events_parquet",
        }
        for query in queries:
            query.processAllAvailable()
        assert spark.read.parquet(paths.event_details).count() == 7
        assert spark.read.parquet(paths.suspicious).count() == 2
        assert spark.read.schema(analytics().trend_windows(initial, "10 minutes", config()).schema)\
            .parquet(paths.gold_trends).count() == 0
        advance = event(meta={"id":"clock", "dt":"2026-01-01T00:20:00Z"})
        transform.normalize_events(transform.parse_events(kafka_rows(spark, [advance])), settings())\
            .write.mode("append").parquet(str(source))
        for query in queries:
            query.processAllAvailable()
        assert all(query.isActive and query.exception() is None for query in queries)
        assert spark.read.parquet(paths.event_details).count() == 8
        gold = spark.read.parquet(paths.gold_trends).filter(
            "window_start = TIMESTAMP '2026-01-01 00:00:00'"
        ).collect()
        expected = json.loads((FIXTURES / "week_two_expected.json").read_text())["trends"]
        assert len(gold) == len(expected)
        actual = {(row.wiki, row.page_key): row for row in gold}
        for wanted in expected:
            row = actual[(wanted["wiki"], wanted["page_key"])]
            assert row.trend_score == pytest.approx(wanted["trend_score"])
            assert row.edit_count == wanted["edit_count"]
        provisional = spark.read.parquet(paths.provisional_trends)
        assert "batch_id" in provisional.columns
        assert provisional.filter("window_start = TIMESTAMP '2026-01-01 00:00:00'").count() == 3
    finally:
        for query in reversed(queries):
            query.stop()
