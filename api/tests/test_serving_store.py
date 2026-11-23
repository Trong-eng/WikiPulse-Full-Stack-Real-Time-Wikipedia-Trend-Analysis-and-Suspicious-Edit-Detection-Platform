"""Contract v0.2 store: trends, suspicious edits and event detail (W2-NHAN-01)."""

from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc
T0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


@pytest.fixture
def store(settings, cassandra_boundary):
    from wikipulse_core.serving import CassandraActivityStore

    store = CassandraActivityStore(settings)
    yield store
    store.close()


def at(row, minutes, **changes):
    """Shift every window/bucket/event timestamp of a row by whole minutes."""
    shifted = {
        key: value + timedelta(minutes=minutes) if isinstance(value, datetime) else value
        for key, value in row.items()
    }
    return {**shifted, **changes}


def test_store_satisfies_the_spark_analytics_writer(store):
    from processing.spark.wikipulse.sinks import AnalyticsBatchWriter

    AnalyticsBatchWriter(store)  # Raises if any upsert method is missing.


def test_trend_retries_replace_rows_and_latest_window_comes_from_the_index(
    store, cassandra_boundary, trend_row
):
    store.upsert_trends(iter([trend_row, trend_row]))
    store.upsert_trends([at(trend_row, 1), {**at(trend_row, 1), "edit_count": 9}])

    assert len(cassandra_boundary.tables["page_trends_by_window"]) == 2
    assert len(cassandra_boundary.tables["trend_windows_by_wiki"]) == 2
    window, rows = store.get_trends("enwiki")
    assert window == T0 + timedelta(minutes=1)
    assert [row["edit_count"] for row in rows] == [9]
    assert rows[0]["window_start"].tzinfo == UTC


def test_trends_sort_by_score_then_edits_then_page_key_and_apply_limit(store, trend_row):
    store.upsert_trends([
        {**trend_row, "page_key": "b", "trend_score": 0.5, "edit_count": 2},
        {**trend_row, "page_key": "a", "trend_score": 0.5, "edit_count": 2},
        {**trend_row, "page_key": "c", "trend_score": 0.5, "edit_count": 3},
        {**trend_row, "page_key": "d", "trend_score": 0.9, "edit_count": 1},
    ])
    window, rows = store.get_trends("enwiki", window=T0, limit=3)
    assert window == T0
    assert [row["page_key"] for row in rows] == ["d", "c", "a"]


def test_missing_trend_window_returns_no_window(store, trend_row):
    assert store.get_trends("enwiki") == (None, [])
    store.upsert_trends([trend_row])
    assert store.get_trends("enwiki", window=T0 + timedelta(minutes=3)) == (None, [])
    assert store.get_trends("viwiki") == (None, [])


def test_trend_partition_over_capacity_fails_instead_of_truncating(store, trend_row):
    from wikipulse_core.serving import CAPACITY_LIMIT, CapacityExceeded

    store.upsert_trends({**trend_row, "page_key": str(n)} for n in range(CAPACITY_LIMIT + 1))
    with pytest.raises(CapacityExceeded):
        store.get_trends("enwiki")


def test_suspicious_edits_read_recent_buckets_and_sort_by_risk(store, suspicious_row):
    store.upsert_suspicious_edits([
        suspicious_row,
        at(suspicious_row, 1, event_id="b", risk_score=10, risk_reasons=["ANONYMOUS_EDIT"]),
        at(suspicious_row, 2, event_id="c", risk_score=30),
        at(suspicious_row, 9, event_id="old-window-anchor", risk_score=10,
           risk_reasons=["REVERT_PATTERN"]),
    ])
    latest = store.get_suspicious_edits("enwiki", minutes=5)
    assert [row["event_id"] for row in latest] == ["old-window-anchor"]

    rows = store.get_suspicious_edits("enwiki", window=T0 + timedelta(minutes=2), minutes=3)
    assert [row["event_id"] for row in rows] == ["c", "fixture-004", "b"]
    assert store.get_suspicious_edits(
        "enwiki", window=T0 + timedelta(minutes=2), minutes=3, min_score=20, limit=1
    )[0]["event_id"] == "c"
    assert store.get_suspicious_edits("enwiki", window=T0 - timedelta(minutes=1)) == []


def test_suspicious_window_inside_a_minute_uses_that_bucket(store, suspicious_row):
    store.upsert_suspicious_edits([suspicious_row])
    rows = store.get_suspicious_edits("enwiki", window=T0 + timedelta(seconds=45), minutes=1)
    assert [row["event_id"] for row in rows] == ["fixture-004"]


def test_suspicious_rows_over_capacity_across_buckets_fail(store, suspicious_row):
    from wikipulse_core.serving import CAPACITY_LIMIT, CapacityExceeded

    half = CAPACITY_LIMIT // 2 + 1
    store.upsert_suspicious_edits(
        at(suspicious_row, minute, event_id=f"{minute}-{n}")
        for minute in (0, 1) for n in range(half)
    )
    with pytest.raises(CapacityExceeded):
        store.get_suspicious_edits("enwiki", minutes=2)


def test_suspicious_and_event_retries_rewrite_the_same_keys(
    store, cassandra_boundary, suspicious_row, event_row
):
    store.upsert_suspicious_edits([suspicious_row, suspicious_row])
    store.upsert_suspicious_edits([{**suspicious_row, "risk_score": 50,
                                    "risk_reasons": ["LARGE_DELETION", "REVERT_PATTERN"]}])
    store.upsert_events([event_row, event_row])
    store.upsert_events([{**event_row, "risk_score": 50}])

    assert len(cassandra_boundary.tables["suspicious_edits_by_bucket"]) == 1
    assert len(cassandra_boundary.tables["suspicious_buckets_by_wiki"]) == 1
    assert len(cassandra_boundary.tables["events_by_id"]) == 1
    assert [row["risk_score"] for row in store.get_suspicious_edits("enwiki")] == [50]
    assert store.get_event("fixture-004")["risk_score"] == 50


def test_event_detail_round_trip_keeps_empty_reasons_as_list(store, event_row):
    store.upsert_events([
        event_row,
        {**event_row, "event_id": "plain", "risk_score": 0, "risk_reasons": []},
    ])
    assert store.get_event("fixture-004")["risk_reasons"] == ["LARGE_DELETION"]
    plain = store.get_event("plain")
    assert (plain["risk_score"], plain["risk_reasons"]) == (0, [])
    assert plain["event_time"].tzinfo == UTC
    assert store.get_event("missing") is None


def test_risk_reasons_are_returned_in_contract_order(store, event_row):
    store.upsert_events([{
        **event_row, "risk_score": 60,
        "risk_reasons": ["ANONYMOUS_EDIT", "LARGE_DELETION", "REVERT_PATTERN"],
    }])
    assert store.get_event("fixture-004")["risk_reasons"] == [
        "LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT"
    ]


@pytest.mark.parametrize(
    "method, fixture, override",
    [
        ("upsert_trends", "trend_row", {"window_end": datetime(2026, 1, 1, 0, 1)}),
        ("upsert_trends", "trend_row", {"trend_score": 1.5}),
        ("upsert_trends", "trend_row", {"page_key": ""}),
        ("upsert_trends", "trend_row", {"user_hash": "abc"}),
        ("upsert_suspicious_edits", "suspicious_row", {"risk_score": 0}),
        ("upsert_suspicious_edits", "suspicious_row", {"risk_reasons": ["VANDAL"]}),
        ("upsert_suspicious_edits", "suspicious_row", {"risk_reasons": []}),
        ("upsert_suspicious_edits", "suspicious_row",
         {"bucket_start": datetime(2026, 1, 1, 0, 1, tzinfo=UTC)}),
        ("upsert_suspicious_edits", "suspicious_row", {"user_hash": "abc"}),
        ("upsert_events", "event_row", {"risk_score": 101}),
        ("upsert_events", "event_row", {"comment": "raw text"}),
        ("upsert_events", "event_row", {"wiki": "enwiki' OR 1=1"}),
    ],
)
def test_rows_that_break_contract_v02_fail_the_batch(
    store, cassandra_boundary, request, method, fixture, override
):
    with pytest.raises(ValueError):
        getattr(store, method)([{**request.getfixturevalue(fixture), **override}])
    assert not any(cassandra_boundary.tables.values())


@pytest.mark.parametrize("minutes", [0, 16])
def test_suspicious_minutes_outside_contract_are_rejected(store, minutes):
    with pytest.raises(ValueError):
        store.get_suspicious_edits("enwiki", minutes=minutes)
