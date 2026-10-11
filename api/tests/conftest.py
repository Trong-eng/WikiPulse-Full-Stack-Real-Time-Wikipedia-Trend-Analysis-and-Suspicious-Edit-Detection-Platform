import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def restore_root_logging_after_api_tests():
    root = logging.getLogger()
    original_handlers, original_level = root.handlers[:], root.level
    yield
    for handler in root.handlers:
        if handler not in original_handlers:
            handler.close()
    root.handlers, root.level = original_handlers, original_level


@pytest.fixture
def settings():
    return SimpleNamespace(
        cassandra_host="cassandra",
        cassandra_port=9042,
        cassandra_keyspace="wikipulse",
        pipeline_mode="REPLAY",
        wiki_allowlist=("enwiki", "viwiki"),
    )


@pytest.fixture
def activity_row():
    return {
        "wiki": "enwiki",
        "window_start": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        "window_end": datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
        "event_count": 5,
        "edit_count": 3,
        "new_page_count": 2,
        "anonymous_edit_count": 1,
        "bot_edit_count": 1,
        "updated_at": datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc),
    }


class FakeResult(list):
    def one(self):
        return self[0] if self else None


class CassandraBoundary:
    """Cassandra's external connection boundary, retaining key/INSERT semantics."""

    def __init__(self):
        self.rows = {}
        self.connect_failures = 0
        self.query_failure = False
        self.clusters = []
        self.schema_statements = []

    def cluster(self, contact_points, port, **kwargs):
        assert contact_points == ["cassandra"]
        assert port == 9042
        cluster = FakeCluster(self)
        self.clusters.append(cluster)
        return cluster


class FakeCluster:
    def __init__(self, boundary):
        self.boundary = boundary
        self.closed = False

    def connect(self, keyspace=None):
        if self.boundary.connect_failures:
            self.boundary.connect_failures -= 1
            raise ConnectionError("Cassandra unavailable")
        return FakeSession(self.boundary, keyspace)

    def shutdown(self):
        self.closed = True


class FakeSession:
    def __init__(self, boundary, keyspace):
        self.boundary = boundary
        self.keyspace = keyspace

    def set_keyspace(self, keyspace):
        self.keyspace = keyspace

    def prepare(self, statement):
        return statement

    def execute(self, statement, parameters=None):
        if self.boundary.query_failure:
            raise ConnectionError("Cassandra unavailable")
        normalized = " ".join(statement.split()).lower()
        if normalized.startswith("create "):
            self.boundary.schema_statements.append(statement)
            return FakeResult()
        if "from system.local" in normalized:
            return FakeResult([SimpleNamespace(release_version="4.1")])
        if normalized.startswith("insert into"):
            columns = statement.split("(", 1)[1].split(")", 1)[0]
            row = dict(zip((column.strip() for column in columns.split(",")), parameters))
            assert set(row) == {
                "wiki",
                "window_start",
                "window_end",
                "event_count",
                "edit_count",
                "new_page_count",
                "anonymous_edit_count",
                "bot_edit_count",
                "updated_at",
            }
            self.boundary.rows[(row["wiki"], row["window_start"])] = row
            return FakeResult()
        assert "allow filtering" not in normalized
        assert "where wiki = ?" in normalized
        wiki = parameters[0]
        selected = [row for row in self.boundary.rows.values() if row["wiki"] == wiki]
        if "window_start = ?" in normalized:
            selected = [
                row
                for row in selected
                if utc_value(row["window_start"]) == utc_value(parameters[1])
            ]
        selected.sort(key=lambda row: utc_value(row["window_start"]), reverse=True)
        selected = selected[: parameters[-1]]
        return FakeResult([SimpleNamespace(**row) for row in selected])


def utc_value(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


@pytest.fixture
def cassandra_boundary(monkeypatch):
    from wikipulse_core import serving

    boundary = CassandraBoundary()
    monkeypatch.setattr(serving, "Cluster", boundary.cluster)
    return boundary
