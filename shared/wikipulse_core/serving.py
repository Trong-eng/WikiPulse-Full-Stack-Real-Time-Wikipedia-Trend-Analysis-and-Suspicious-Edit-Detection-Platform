"""Driver-side Cassandra serving contract for absolute activity snapshots."""

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wikipulse_core.config import Settings


def Cluster(*args, **kwargs):
    """Load the optional driver only when a service first needs Cassandra."""
    from cassandra.cluster import Cluster as DriverCluster

    return DriverCluster(*args, **kwargs)


class ActivityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wiki: str
    window_start: datetime
    window_end: datetime
    event_count: int = Field(ge=0)
    edit_count: int = Field(ge=0)
    new_page_count: int = Field(ge=0)
    anonymous_edit_count: int = Field(ge=0)
    bot_edit_count: int = Field(ge=0)
    updated_at: datetime

    @field_validator("window_start", "window_end", "updated_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        # Spark and cassandra-driver use naive datetimes to represent UTC.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


ACTIVITY_FIELDS = tuple(ActivityRow.model_fields)


class CassandraActivityStore:
    """Open one driver session lazily; retries replace totals at a stable row key."""

    def __init__(self, settings: Settings):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", settings.cassandra_keyspace):
            raise ValueError("CASSANDRA_KEYSPACE must be a CQL identifier")
        self.settings = settings
        self._cluster = None
        self._session = None
        self._prepared = {}
        self._lock = RLock()

    def _connect(self):
        with self._lock:
            if self._session is None:
                cluster = Cluster(
                    [self.settings.cassandra_host],
                    port=self.settings.cassandra_port,
                    connect_timeout=5,
                    control_connection_timeout=5,
                )
                try:
                    session = cluster.connect(self.settings.cassandra_keyspace)
                    session.default_timeout = 5
                except Exception:
                    cluster.shutdown()
                    raise
                self._cluster, self._session = cluster, session
            return self._session

    def _statement(self, query: str):
        with self._lock:
            session = self._connect()
            if query not in self._prepared:
                self._prepared[query] = session.prepare(query)
            return self._prepared[query]

    def upsert_activity(self, rows: Iterable[dict]) -> None:
        columns = ", ".join(ACTIVITY_FIELDS)
        placeholders = ", ".join("?" for _ in ACTIVITY_FIELDS)
        query = f"INSERT INTO wiki_activity_by_window ({columns}) VALUES ({placeholders})"
        for source in rows:
            row = ActivityRow.model_validate(source).model_dump()
            self._connect().execute(
                self._statement(query), tuple(row[field] for field in ACTIVITY_FIELDS)
            )

    def get_activity(
        self, wiki: str, window: datetime | None = None, limit: int = 20
    ) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = f"SELECT {', '.join(ACTIVITY_FIELDS)} FROM wiki_activity_by_window WHERE wiki = ?"
        values: tuple = (wiki,)
        if window is not None:
            query += " AND window_start = ?"
            values += (ActivityRow.utc_timestamp(window),)
        query += " LIMIT ?"
        result = self._connect().execute(self._statement(query), values + (limit,))
        return [
            ActivityRow.model_validate(
                {field: getattr(row, field) for field in ACTIVITY_FIELDS}
            ).model_dump()
            for row in result
        ]

    def health(self) -> bool:
        result = self._connect().execute("SELECT release_version FROM system.local")
        return result.one() is not None

    def close(self) -> None:
        with self._lock:
            if self._cluster is not None:
                self._cluster.shutdown()
            self._cluster = self._session = None
            self._prepared.clear()
