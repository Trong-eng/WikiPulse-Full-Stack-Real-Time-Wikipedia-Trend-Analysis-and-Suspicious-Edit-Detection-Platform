"""Driver-side Cassandra writes use replay-safe absolute window counts."""

from datetime import datetime, timezone


def _utc_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return value


class ActivityBatchWriter:
    def __init__(self, store):
        self.store = store

    def write_activity_batch(self, batch_df, batch_id):
        """Let sink errors fail the query; checkpoint retry re-upserts the same values."""
        def rows():
            for row in batch_df.toLocalIterator():
                values = row.asDict(recursive=True) if hasattr(row, "asDict") else dict(row)
                yield {key: _utc_value(value) for key, value in values.items()}

        self.store.upsert_activity(rows())


class AnalyticsBatchWriter:
    """Producer adapter; storage implementation belongs to the Cassandra owner."""

    METHODS = ("upsert_trends", "upsert_suspicious_edits", "upsert_events")

    def __init__(self, store):
        missing = [name for name in self.METHODS if not callable(getattr(store, name, None))]
        if missing:
            raise ValueError("Cassandra analytics store missing: " + ", ".join(missing))
        self.store = store

    def _write(self, method, batch_df):
        rows = (
            {key: _utc_value(value) for key, value in row.asDict(recursive=True).items()}
            for row in batch_df.toLocalIterator()
        )
        getattr(self.store, method)(rows)

    def write_trends_batch(self, batch_df, batch_id):
        self._write("upsert_trends", batch_df)

    def write_suspicious_batch(self, batch_df, batch_id):
        self._write("upsert_suspicious_edits", batch_df)

    def write_events_batch(self, batch_df, batch_id):
        self._write("upsert_events", batch_df)


class TrendChangelogWriter:
    """One absolute-update snapshot per batch; retries overwrite that same batch path."""

    def __init__(self, path):
        self.path = path.rstrip("/")

    def write_batch(self, batch_df, batch_id):
        if not isinstance(batch_id, int) or batch_id < 0:
            raise ValueError("batch_id must be a nonnegative integer")
        batch_df.write.mode("overwrite").parquet(f"{self.path}/batch_id={batch_id}")
