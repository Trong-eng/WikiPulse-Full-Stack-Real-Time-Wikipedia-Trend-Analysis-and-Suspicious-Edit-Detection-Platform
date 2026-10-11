"""Catch driver contracts that can be verified without a running JVM."""

from datetime import datetime, timezone
from importlib import import_module, util
from threading import Event
from types import SimpleNamespace

import pytest


def implementation(name):
    module = f"processing.spark.wikipulse.{name}"
    assert util.find_spec(module) is not None, f"Missing CP0 implementation: {module}"
    return import_module(module)


def test_paths_isolate_each_run_and_stream_checkpoint():
    settings = SimpleNamespace(
        data_base_path="file:///data/wikipulse/",
        spark_checkpoint_path="/data/checkpoints/",
        run_id="smoke-123",
    )
    paths = implementation("paths").PipelinePaths.from_settings(settings)
    assert paths.bronze_raw == "file:///data/wikipulse/smoke-123/bronze/raw"
    assert paths.bronze_invalid == "file:///data/wikipulse/smoke-123/bronze/invalid"
    assert paths.silver == "file:///data/wikipulse/smoke-123/silver/events"
    assert paths.gold_activity == "file:///data/wikipulse/smoke-123/gold/activity"
    assert paths.checkpoint("activity_gold") == "/data/checkpoints/smoke-123/activity_gold"
    assert paths.checkpoint("silver_events") != paths.checkpoint("activity_gold")


class IteratorBatch:
    """Deliberately lacks collect(); batches must stream rows at the driver."""

    def __init__(self, rows):
        self.rows = rows

    def toLocalIterator(self):
        yield from self.rows


class CapturingStore:
    def __init__(self):
        self.rows = []

    def upsert_activity(self, rows):
        assert not isinstance(rows, list), "Driver must avoid materializing the full batch"
        self.rows.extend(rows)


def test_activity_writer_keeps_absolute_counts_and_converts_timestamps_to_utc():
    sinks = implementation("sinks")
    row = {
        "wiki": "enwiki",
        "window_start": datetime(2024, 1, 1, 12, 0),
        "window_end": datetime(2024, 1, 1, 12, 1),
        "event_count": 5,
        "edit_count": 3,
        "new_page_count": 1,
        "anonymous_edit_count": 2,
        "bot_edit_count": 1,
        "updated_at": datetime(2024, 1, 1, 12, 0, 50),
    }
    store = CapturingStore()
    writer = sinks.ActivityBatchWriter(store)
    writer.write_activity_batch(IteratorBatch([row]), 7)
    writer.write_activity_batch(IteratorBatch([row]), 7)
    assert [value["event_count"] for value in store.rows] == [5, 5]
    assert store.rows[0]["window_start"] == datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    assert store.rows[0]["updated_at"].tzinfo is timezone.utc


def test_activity_writer_propagates_cassandra_failure():
    class FailingStore:
        def upsert_activity(self, rows):
            raise ConnectionError("Cassandra unavailable")

    writer = implementation("sinks").ActivityBatchWriter(FailingStore())
    with pytest.raises(ConnectionError, match="Cassandra unavailable"):
        writer.write_activity_batch(IteratorBatch([]), 0)


def test_query_failure_bubbles_from_supervisor():
    failure = RuntimeError("checkpoint corrupt")
    query = SimpleNamespace(name="silver_events", isActive=False, exception=lambda: failure)
    spark = SimpleNamespace(streams=SimpleNamespace(awaitAnyTermination=lambda timeout: True))
    with pytest.raises(RuntimeError, match="silver_events") as caught:
        implementation("supervisor").supervise_queries(spark, [query], Event())
    assert caught.value.__cause__ is failure


def test_unexpected_clean_query_exit_does_not_leave_partial_pipeline_alive():
    query = SimpleNamespace(name="bronze_raw", isActive=False, exception=lambda: None)
    spark = SimpleNamespace(streams=SimpleNamespace(awaitAnyTermination=lambda timeout: True))
    with pytest.raises(RuntimeError, match="bronze_raw.*terminated"):
        implementation("supervisor").supervise_queries(spark, [query], Event())


def test_cleanup_closes_every_resource_even_when_one_stop_fails():
    events = []

    class Query:
        isActive = True

        def __init__(self, name, fails=False):
            self.name = name
            self.fails = fails

        def stop(self):
            events.append(self.name)
            if self.fails:
                raise RuntimeError("already disconnected")

    store = SimpleNamespace(close=lambda: events.append("store"))
    spark = SimpleNamespace(stop=lambda: events.append("spark"))
    implementation("supervisor").close_pipeline(
        [Query("raw", fails=True), Query("silver")], store, spark
    )
    assert events == ["silver", "raw", "store", "spark"]


def test_progress_file_has_query_progress_for_smoke_phase_barrier(tmp_path):
    import json

    path = tmp_path / "progress.json"
    queries = [
        SimpleNamespace(name="silver_events", isActive=True,
                        lastProgress={"batchId": 2, "numInputRows": 8}),
        SimpleNamespace(name="activity_gold", isActive=True, lastProgress=None),
    ]
    implementation("supervisor").publish_progress(path, queries)
    result = json.loads(path.read_text())
    assert result["queries"]["silver_events"]["numInputRows"] == 8
    assert result["queries"]["activity_gold"] is None
    assert result["updated_at"].endswith("Z")
    assert result["active_queries"] == {"silver_events": True, "activity_gold": True}


def test_startup_failure_stops_queries_already_started_and_closes_driver_resources():
    module = "processing.spark.jobs.streaming_job"
    assert util.find_spec(module) is not None, "Missing streaming job implementation"
    job = import_module(module)
    events = []
    spark = SimpleNamespace(stop=lambda: events.append("spark"))
    store = SimpleNamespace(close=lambda: events.append("store"))
    query = SimpleNamespace(name="bronze_raw", isActive=True,
                            stop=lambda: events.append("bronze_raw"))

    def start_queries(spark, settings, store, queries):
        queries.append(query)
        raise RuntimeError("Silver cannot start")

    with pytest.raises(RuntimeError, match="Silver cannot start"):
        job.run_pipeline(
            SimpleNamespace(), spark_factory=lambda settings: spark,
            store_factory=lambda settings: store, query_starter=start_queries,
        )
    assert events == ["bronze_raw", "store", "spark"]
