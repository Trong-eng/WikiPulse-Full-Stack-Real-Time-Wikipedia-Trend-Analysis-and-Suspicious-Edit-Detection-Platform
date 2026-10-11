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
    assert len(cassandra_boundary.schema_statements) == 2
    assert "CREATE KEYSPACE IF NOT EXISTS wikipulse" in cassandra_boundary.schema_statements[0]
    assert "PRIMARY KEY ((wiki), window_start)" in cassandra_boundary.schema_statements[1]
    assert "CLUSTERING ORDER BY (window_start DESC)" in cassandra_boundary.schema_statements[1]
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
