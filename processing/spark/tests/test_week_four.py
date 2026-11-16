"""Release regression: literal expectations independent of scoring expressions."""

from datetime import datetime

import pytest

from processing.spark.tests.test_transformations import event, kafka_rows, settings, transformations
from processing.spark.tests.test_week_two import analytics, config

pytestmark = pytest.mark.spark


def test_combined_risk_rules_and_non_edit_exclusion(spark):
    transform = transformations()
    payloads = [
        event(user="SyntheticEditor", anon=True, comment="Reverted edit",
              length={"old": 1000, "new": 500}, type=kind, bot=bot)
        for kind, bot in [("edit", False), ("edit", True), ("new", False), ("log", False)]
    ]
    silver = transform.normalize_events(transform.parse_events(kafka_rows(spark, payloads)), settings())
    rows = analytics().score_events(silver, config()).orderBy("kafka_offset").collect()
    assert [row.risk_score for row in rows] == [60, 50, 0, 0]
    assert [row.risk_reasons for row in rows] == [
        ["LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT"],
        ["LARGE_DELETION", "REVERT_PATTERN"], [], [],
    ]


def test_trend_half_open_boundary_and_metadata_tie_are_order_independent(spark):
    transform = transformations()
    payloads = [
        event(meta={"id": identifier, "dt": instant}, title=title, namespace=namespace,
              user="SyntheticEditor", anon=False, length={"old": 100, "new": 120})
        for identifier, instant, title, namespace in [
            # Title and namespace order oppose event_id: b must win the time tie.
            ("a", "2026-01-01T00:00:00Z", "Zulu", 2),
            ("b", "2026-01-01T00:00:00Z", "Alpha", 1),
            ("c", "2026-01-01T00:05:00Z", "NextWindow", 0),
        ]
    ]
    for ordered in (payloads, list(reversed(payloads))):
        silver = transform.normalize_events(
            transform.parse_events(kafka_rows(spark, ordered)), settings()
        )
        rows = analytics().trend_windows(silver, "10 minutes", config()).filter(
            "window_start IN (TIMESTAMP '2026-01-01 00:00:00', "
            "TIMESTAMP '2026-01-01 00:05:00')"
        ).orderBy("window_start").collect()
        assert len(rows) == 2
        assert rows[0].window_start == datetime(2026, 1, 1)
        assert (rows[0].edit_count, rows[0].unique_editors, rows[0].abs_byte_delta,
                rows[0].page_title, rows[0].namespace) == (2, 1, 40, "Alpha", 1)
        assert rows[0].trend_score == pytest.approx(0.0335)
        assert (rows[1].edit_count, rows[1].page_title, rows[1].namespace) == (1, "NextWindow", 0)
        assert rows[1].trend_score == pytest.approx(0.023)
