"""Driver-side Cassandra serving contract: activity (v0.1), trends/suspicious/detail (v0.2)."""

import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wikipulse_core.config import Settings

WIKI_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"
# plans.md: top-N reads a whole partition, then sorts; beyond this the API reports an error.
CAPACITY_LIMIT = 5000
TREND_WINDOW = timedelta(minutes=5)
MAX_SUSPICIOUS_MINUTES = 15
RISK_REASONS = ("LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT")
RiskReason = Literal["LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT"]


class CapacityExceeded(RuntimeError):
    """A query would read more than CAPACITY_LIMIT rows; ranking is never truncated."""


def _utc(value: datetime) -> datetime:
    # Spark and cassandra-driver use naive datetimes to represent UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def Cluster(*args, **kwargs):
    """Load the optional driver only when a service first needs Cassandra."""
    from cassandra.cluster import Cluster as DriverCluster

    return DriverCluster(*args, **kwargs)


class ActivityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wiki: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
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

    @model_validator(mode="after")
    def consistent_window_counts(self) -> "ActivityRow":
        # Mirrors activity_windows: anonymous/bot counts are subsets of edits.
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.edit_count + self.new_page_count > self.event_count:
            raise ValueError("edit_count + new_page_count must not exceed event_count")
        if max(self.anonymous_edit_count, self.bot_edit_count) > self.edit_count:
            raise ValueError("anonymous/bot edit counts must not exceed edit_count")
        return self


ACTIVITY_FIELDS = tuple(ActivityRow.model_fields)


class _ServingRow(BaseModel):
    """Contract v0.2 rows: exact fields (no user/comment can slip in), UTC timestamps."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def utc_timestamps(cls, value):
        return _utc(value) if isinstance(value, datetime) else value


def _reasons(value) -> list:
    """Spark sends arrays, Cassandra returns a set or None (empty set); keep contract order."""
    reasons = list(value or [])
    order = {name: index for index, name in enumerate(RISK_REASONS)}
    return sorted(set(reasons), key=lambda name: order.get(name, len(order)))


class TrendRow(_ServingRow):
    wiki: str = Field(pattern=WIKI_PATTERN)
    window_start: datetime
    window_end: datetime
    page_key: str = Field(min_length=1)
    page_title: str | None = None
    namespace: int | None = None
    edit_count: int = Field(ge=0)
    unique_editors: int = Field(ge=0)
    abs_byte_delta: int = Field(ge=0)
    # Weighted sum of capped ratios; allow float rounding just above 1.
    trend_score: float = Field(ge=0, le=1 + 1e-9)
    updated_at: datetime

    @model_validator(mode="after")
    def five_minute_window(self) -> "TrendRow":
        if self.window_end - self.window_start != TREND_WINDOW:
            raise ValueError("trend window must span exactly 5 minutes")
        return self


class SuspiciousEditRow(_ServingRow):
    wiki: str = Field(pattern=WIKI_PATTERN)
    bucket_start: datetime
    event_id: str = Field(min_length=1)
    event_time: datetime
    page_key: str = Field(min_length=1)
    page_title: str | None = None
    revision_new: int | None = None
    byte_delta: int | None = None
    is_anonymous: bool
    is_bot: bool
    risk_score: int = Field(ge=1, le=100)
    risk_reasons: list[RiskReason] = Field(min_length=1)
    updated_at: datetime

    @field_validator("risk_reasons", mode="before")
    @classmethod
    def ordered_reasons(cls, value):
        return _reasons(value)

    @model_validator(mode="after")
    def minute_bucket(self) -> "SuspiciousEditRow":
        if self.bucket_start != self.event_time.replace(second=0, microsecond=0):
            raise ValueError("bucket_start must be the event_time minute")
        return self


class EventDetailRow(_ServingRow):
    event_id: str = Field(min_length=1)
    wiki: str = Field(pattern=WIKI_PATTERN)
    event_time: datetime
    page_key: str = Field(min_length=1)
    page_title: str | None = None
    namespace: int | None = None
    event_type: str
    revision_old: int | None = None
    revision_new: int | None = None
    length_old: int | None = None
    length_new: int | None = None
    byte_delta: int | None = None
    is_anonymous: bool
    is_bot: bool
    is_minor: bool | None = None
    risk_score: int = Field(ge=0, le=100)
    risk_reasons: list[RiskReason]
    pipeline_version: str
    processed_at: datetime

    @field_validator("risk_reasons", mode="before")
    @classmethod
    def ordered_reasons(cls, value):
        return _reasons(value)


TREND_FIELDS = tuple(TrendRow.model_fields)
SUSPICIOUS_FIELDS = tuple(SuspiciousEditRow.model_fields)
EVENT_FIELDS = tuple(EventDetailRow.model_fields)


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

    # --- Contract v0.2: written by AnalyticsBatchWriter (Spark foreachBatch), read by the API.

    def _upsert(self, table, model, fields, rows, index=None, index_key=None) -> None:
        """Rows first, then the index of windows/buckets that now have rows (retry-safe)."""
        query = (
            f"INSERT INTO {table} ({', '.join(fields)}) "
            f"VALUES ({', '.join('?' for _ in fields)})"
        )
        latest = {}
        for source in rows:
            row = model.model_validate(source).model_dump()
            self._connect().execute(self._statement(query), tuple(row[f] for f in fields))
            if index:
                key = (row["wiki"], row[index_key])
                latest[key] = max(latest.get(key, row["updated_at"]), row["updated_at"])
        if index:
            statement = self._statement(
                f"INSERT INTO {index} (wiki, {index_key}, updated_at) VALUES (?, ?, ?)"
            )
            for (wiki, start), updated_at in latest.items():
                self._connect().execute(statement, (wiki, start, updated_at))

    def upsert_trends(self, rows: Iterable[dict]) -> None:
        self._upsert("page_trends_by_window", TrendRow, TREND_FIELDS, rows,
                     "trend_windows_by_wiki", "window_start")

    def upsert_suspicious_edits(self, rows: Iterable[dict]) -> None:
        self._upsert("suspicious_edits_by_bucket", SuspiciousEditRow, SUSPICIOUS_FIELDS, rows,
                     "suspicious_buckets_by_wiki", "bucket_start")

    def upsert_events(self, rows: Iterable[dict]) -> None:
        self._upsert("events_by_id", EventDetailRow, EVENT_FIELDS, rows)

    def _select(self, query: str, values: tuple) -> list:
        return list(self._connect().execute(self._statement(query), values))

    def _latest(self, index: str, column: str, wiki: str) -> datetime | None:
        rows = self._select(f"SELECT {column} FROM {index} WHERE wiki = ? LIMIT ?", (wiki, 1))
        return _utc(getattr(rows[0], column)) if rows else None

    def get_trends(
        self, wiki: str, window: datetime | None = None, limit: int = 20
    ) -> tuple[datetime | None, list[dict]]:
        """Top-N of one window (latest when omitted); (None, []) when it has no rows."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        start = _utc(window) if window else self._latest("trend_windows_by_wiki", "window_start", wiki)
        if start is None:
            return None, []
        result = self._select(
            f"SELECT {', '.join(TREND_FIELDS)} FROM page_trends_by_window "
            "WHERE wiki = ? AND window_start = ? LIMIT ?",
            (wiki, start, CAPACITY_LIMIT + 1),
        )
        if len(result) > CAPACITY_LIMIT:
            raise CapacityExceeded(f"trend window has more than {CAPACITY_LIMIT} rows")
        rows = [
            TrendRow.model_validate({f: getattr(row, f) for f in TREND_FIELDS}).model_dump()
            for row in result
        ]
        if not rows:
            return None, []
        rows.sort(key=lambda row: (-row["trend_score"], -row["edit_count"], row["page_key"]))
        return start, rows[:limit]

    def get_suspicious_edits(
        self, wiki: str, window: datetime | None = None, minutes: int = 5,
        min_score: int = 0, limit: int = 20,
    ) -> list[dict]:
        """Edits of the `minutes` buckets ending at `window` (or the latest bucket)."""
        if not 1 <= minutes <= MAX_SUSPICIOUS_MINUTES:
            raise ValueError(f"minutes must be between 1 and {MAX_SUSPICIOUS_MINUTES}")
        if not 1 <= limit <= 100 or not 0 <= min_score <= 100:
            raise ValueError("limit must be 1-100 and min_score 0-100")
        anchor = (
            _utc(window).replace(second=0, microsecond=0) if window
            else self._latest("suspicious_buckets_by_wiki", "bucket_start", wiki)
        )
        if anchor is None:
            return []
        buckets = self._select(
            "SELECT bucket_start FROM suspicious_buckets_by_wiki "
            "WHERE wiki = ? AND bucket_start <= ? AND bucket_start > ? LIMIT ?",
            (wiki, anchor, anchor - timedelta(minutes=minutes), minutes),
        )
        query = (
            f"SELECT {', '.join(SUSPICIOUS_FIELDS)} FROM suspicious_edits_by_bucket "
            "WHERE wiki = ? AND bucket_start = ? LIMIT ?"
        )
        result = []
        for bucket in buckets:
            remaining = CAPACITY_LIMIT + 1 - len(result)
            result += self._select(query, (wiki, _utc(bucket.bucket_start), remaining))
            if len(result) > CAPACITY_LIMIT:
                raise CapacityExceeded(f"suspicious buckets have more than {CAPACITY_LIMIT} rows")
        rows = [
            SuspiciousEditRow.model_validate(
                {f: getattr(row, f) for f in SUSPICIOUS_FIELDS}
            ).model_dump()
            for row in result
        ]
        rows = [row for row in rows if row["risk_score"] >= min_score]
        # Newest first among equal scores; event_id keeps the order stable between calls.
        rows.sort(key=lambda row: row["event_id"])
        rows.sort(key=lambda row: (row["risk_score"], row["event_time"]), reverse=True)
        return rows[:limit]

    def get_event(self, event_id: str) -> dict | None:
        rows = self._select(
            f"SELECT {', '.join(EVENT_FIELDS)} FROM events_by_id WHERE event_id = ?", (event_id,)
        )
        if not rows:
            return None
        return EventDetailRow.model_validate(
            {f: getattr(rows[0], f) for f in EVENT_FIELDS}
        ).model_dump()

    def health(self) -> bool:
        result = self._connect().execute("SELECT release_version FROM system.local")
        return result.one() is not None

    def close(self) -> None:
        with self._lock:
            if self._cluster is not None:
                self._cluster.shutdown()
            self._cluster = self._session = None
            self._prepared.clear()
