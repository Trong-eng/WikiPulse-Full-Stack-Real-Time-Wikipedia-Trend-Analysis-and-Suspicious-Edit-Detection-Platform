import pytest


def test_schema_initialization_retries_readiness_and_creates_queryable_table(
    settings, cassandra_boundary, monkeypatch
):
    from api.app import init_db

    monkeypatch.setattr(init_db, "Cluster", cassandra_boundary.cluster)
    cassandra_boundary.connect_failures = 2
    waits = []
    init_db.initialize_database(settings, max_attempts=3, retry_delay=0.1, sleep=waits.append)
    assert waits == [0.1, 0.1]
    statements = cassandra_boundary.schema_statements
    assert len(statements) == 7
    assert "CREATE KEYSPACE IF NOT EXISTS wikipulse" in statements[0]
    assert "PRIMARY KEY ((wiki), window_start)" in statements[1]
    assert "CLUSTERING ORDER BY (window_start DESC)" in statements[1]
    keys = {
        "page_trends_by_window": "PRIMARY KEY ((wiki, window_start), page_key)",
        "trend_windows_by_wiki": "PRIMARY KEY ((wiki), window_start)",
        "suspicious_edits_by_bucket": "PRIMARY KEY ((wiki, bucket_start), event_id)",
        "suspicious_buckets_by_wiki": "PRIMARY KEY ((wiki), bucket_start)",
        "events_by_id": "event_id text PRIMARY KEY",
    }
    for table, key in keys.items():
        created = [s for s in statements if f"wikipulse.{table} (" in s]
        assert len(created) == 1 and key in created[0], table
        assert "IF NOT EXISTS" in created[0]
    assert all(cluster.closed for cluster in cassandra_boundary.clusters)


def test_schema_initialization_fails_loud_after_bounded_retries(
    settings, cassandra_boundary, monkeypatch
):
    from api.app import init_db

    monkeypatch.setattr(init_db, "Cluster", cassandra_boundary.cluster)
    cassandra_boundary.connect_failures = 5
    with pytest.raises(
        RuntimeError, match="Cassandra schema initialization failed after 2 attempts"
    ):
        init_db.initialize_database(settings, max_attempts=2, retry_delay=0, sleep=lambda _: None)
    assert len(cassandra_boundary.clusters) == 2
    assert all(cluster.closed for cluster in cassandra_boundary.clusters)
