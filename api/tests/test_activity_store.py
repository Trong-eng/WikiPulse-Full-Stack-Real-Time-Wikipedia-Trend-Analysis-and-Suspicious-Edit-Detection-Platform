from datetime import timedelta, timezone

import pytest


def test_retry_upserts_replace_absolute_counts_for_the_same_window(
    settings, activity_row, cassandra_boundary
):
    from wikipulse_core.serving import CassandraActivityStore

    store = CassandraActivityStore(settings)
    assert not cassandra_boundary.clusters  # Constructing an API must not contact Cassandra.
    store.upsert_activity(iter([activity_row, activity_row]))
    store.upsert_activity([{**activity_row, "event_count": 7, "edit_count": 5}])

    rows = store.get_activity("enwiki")
    assert len(rows) == 1
    assert rows[0]["event_count"] == 7
    assert rows[0]["edit_count"] == 5
    assert set(rows[0]) == set(activity_row)
    store.close()
    assert all(cluster.closed for cluster in cassandra_boundary.clusters)


def test_latest_and_exact_window_queries_return_utc_rows(
    settings, activity_row, cassandra_boundary
):
    from wikipulse_core.serving import CassandraActivityStore

    store = CassandraActivityStore(settings)
    next_row = {
        **activity_row,
        "window_start": activity_row["window_start"] + timedelta(minutes=1),
        "window_end": activity_row["window_end"] + timedelta(minutes=1),
    }
    # cassandra-driver returns naive datetimes representing UTC.
    naive = {
        key: value.replace(tzinfo=None) if hasattr(value, "tzinfo") else value
        for key, value in activity_row.items()
    }
    cassandra_boundary.rows[("enwiki", activity_row["window_start"])] = naive
    store.upsert_activity([next_row])
    assert store.get_activity("enwiki", limit=1)[0]["window_start"] == next_row["window_start"]
    exact = store.get_activity("enwiki", window=activity_row["window_start"])
    assert len(exact) == 1
    assert exact[0]["window_start"].tzinfo == timezone.utc


def test_upsert_rejects_raw_identifiers(settings, activity_row, cassandra_boundary):
    from wikipulse_core.serving import CassandraActivityStore

    with pytest.raises(ValueError):
        CassandraActivityStore(settings).upsert_activity([{**activity_row, "user": "Raw User"}])
    assert not cassandra_boundary.rows


def test_failed_connection_is_closed_and_can_be_retried(settings, cassandra_boundary):
    from wikipulse_core.serving import CassandraActivityStore

    cassandra_boundary.connect_failures = 1
    store = CassandraActivityStore(settings)
    with pytest.raises(ConnectionError):
        store.health()
    assert cassandra_boundary.clusters[0].closed
    assert store.health() is True


def test_invalid_keyspace_cannot_be_interpolated(settings, cassandra_boundary):
    from wikipulse_core.serving import CassandraActivityStore

    settings.cassandra_keyspace = "wikipulse; DROP KEYSPACE other"
    with pytest.raises(ValueError):
        CassandraActivityStore(settings)
    assert not cassandra_boundary.clusters
