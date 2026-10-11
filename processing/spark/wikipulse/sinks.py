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
