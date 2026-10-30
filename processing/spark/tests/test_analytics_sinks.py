from datetime import datetime, timezone

import pytest

from processing.spark.wikipulse.analytics_queries import validate_sink
from processing.spark.wikipulse.sinks import AnalyticsBatchWriter, TrendChangelogWriter


class Row(dict):
    def asDict(self, recursive=False):
        return dict(self)


class Batch:
    def toLocalIterator(self):
        yield Row(wiki="enwiki", page_key="10", edit_count=3,
                  window_start=datetime(2026, 1, 1))


class Store:
    def __init__(self):
        self.rows = []

    def upsert_trends(self, rows):
        assert not isinstance(rows, list)
        self.rows.extend(rows)

    upsert_suspicious_edits = upsert_trends
    upsert_events = upsert_trends


@pytest.mark.parametrize("method", ["write_trends_batch", "write_suspicious_batch", "write_events_batch"])
def test_callbacks_stream_absolute_rows_and_retry_same_values(method):
    store = Store()
    callback = getattr(AnalyticsBatchWriter(store), method)
    callback(Batch(), 4)
    callback(Batch(), 4)
    assert store.rows[0] == store.rows[1]
    assert store.rows[0]["edit_count"] == 3
    assert store.rows[0]["window_start"].tzinfo is timezone.utc


def test_sink_errors_fail_batch():
    class FailingStore(Store):
        def upsert_trends(self, rows):
            raise ConnectionError("sink unavailable")
    with pytest.raises(ConnectionError):
        AnalyticsBatchWriter(FailingStore()).write_trends_batch(Batch(), 0)


def test_sink_mode_is_explicit_and_missing_implementation_fails():
    assert validate_sink("parquet", None) is None
    with pytest.raises(ValueError, match="missing.*upsert_trends"):
        validate_sink("cassandra", object())
    with pytest.raises(ValueError, match="SPARK_ANALYTICS_SINK"):
        validate_sink("invalid", None)


def test_changelog_retry_uses_same_batch_path():
    paths = []
    class Writer:
        def mode(self, mode):
            assert mode == "overwrite"
            return self
        def parquet(self, path):
            paths.append(path)
    class Frame:
        write = Writer()
    writer = TrendChangelogWriter("file:///data/run/provisional/trends/")
    writer.write_batch(Frame(), 7)
    writer.write_batch(Frame(), 7)
    assert paths == ["file:///data/run/provisional/trends/batch_id=7"] * 2
    with pytest.raises(ValueError):
        writer.write_batch(Frame(), -1)
