"""Real Cassandra checks for what the driver fake cannot prove.

Run against any reachable node, e.g. a throwaway container:
CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 pytest -m integration api/tests
"""

import os
import uuid
from datetime import timedelta, timezone

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def real_store(activity_row):
    host = os.environ.get("CASSANDRA_IT_HOST")
    if not host:
        pytest.skip("Set CASSANDRA_IT_HOST to run real Cassandra integration tests")
    from wikipulse_core.config import Settings
    from wikipulse_core.serving import CassandraActivityStore, Cluster

    from api.app.init_db import initialize_database

    keyspace = f"wikipulse_it_{uuid.uuid4().hex[:12]}"
    settings = Settings(
        cassandra_host=host,
        cassandra_port=int(os.environ.get("CASSANDRA_IT_PORT", "9042")),
        cassandra_keyspace=keyspace,
    )
    initialize_database(settings, max_attempts=3, retry_delay=1)
    store = CassandraActivityStore(settings)
    yield store
    store.close()
    cluster = Cluster([settings.cassandra_host], port=settings.cassandra_port)
    try:
        cluster.connect().execute(f"DROP KEYSPACE IF EXISTS {keyspace}")
    finally:
        cluster.shutdown()


def shifted(row, minutes):
    return {
        **row,
        "window_start": row["window_start"] + timedelta(minutes=minutes),
        "window_end": row["window_end"] + timedelta(minutes=minutes),
    }


def test_schema_init_is_idempotent_on_a_real_node(real_store):
    from api.app.init_db import initialize_database

    initialize_database(real_store.settings, max_attempts=1)
    assert real_store.health() is True


def test_retries_replace_absolute_counts_on_the_real_primary_key(real_store, activity_row):
    real_store.upsert_activity([activity_row, activity_row])
    real_store.upsert_activity([{**activity_row, "event_count": 7, "edit_count": 5}])

    rows = real_store.get_activity("enwiki")
    assert len(rows) == 1
    assert (rows[0]["event_count"], rows[0]["edit_count"]) == (7, 5)


def test_latest_windows_come_first_with_bound_limit_and_utc_round_trip(
    real_store, activity_row
):
    real_store.upsert_activity([shifted(activity_row, minute) for minute in range(5)])
    real_store.upsert_activity([{**activity_row, "wiki": "viwiki"}])

    latest = real_store.get_activity("enwiki", limit=3)
    assert [row["window_start"] for row in latest] == [
        activity_row["window_start"] + timedelta(minutes=minute) for minute in (4, 3, 2)
    ]
    assert all(row["window_start"].tzinfo == timezone.utc for row in latest)
    assert all(row["wiki"] == "enwiki" for row in real_store.get_activity("enwiki", limit=100))


def test_exact_window_accepts_non_utc_offsets(real_store, activity_row):
    real_store.upsert_activity([activity_row])
    hanoi = timezone(timedelta(hours=7))

    exact = real_store.get_activity(
        "enwiki", window=activity_row["window_start"].astimezone(hanoi)
    )
    assert [row["window_start"] for row in exact] == [activity_row["window_start"]]
    assert real_store.get_activity("enwiki", window=shifted(activity_row, 9)["window_start"]) == []
