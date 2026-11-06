"""Inspect actual streaming Parquet output inside the Spark image."""

import argparse
import json
import math

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

parser = argparse.ArgumentParser()
parser.add_argument("--base", required=True)
parser.add_argument("--expected", default="tests/fixtures/expected_activity.json")
args = parser.parse_args()
expected = json.load(open(args.expected, encoding="utf-8"))
spark = SparkSession.builder.master("local[1]").appName("WikiPulseSmokeInspect").getOrCreate()
spark.conf.set("spark.sql.session.timeZone", "UTC")
spark.sparkContext.setLogLevel("ERROR")
try:
    counts = {}
    for name, folder, key in [
        ("bronze", "bronze/raw", "raw_total"),
        ("invalid", "bronze/invalid", "invalid_total"),
        ("silver", "silver/events", "silver_total"),
    ]:
        frame = spark.read.parquet(f"{args.base}/{folder}")
        counts[name] = frame.count()
        assert counts[name] == expected[key], (name, counts[name], expected[key])
        if name == "silver":
            assert "user" not in frame.columns and "raw_payload" not in frame.columns
            assert frame.select("event_id").distinct().count() == expected["silver_total"]
    gold = spark.read.parquet(f"{args.base}/gold/activity")
    target = gold.filter("window_start = TIMESTAMP '2026-01-01 00:00:00'")
    rows = {row.wiki: row.asDict() for row in target.collect()}
    assert len(rows) == len(expected["rows"]), rows
    for wanted in expected["rows"]:
        for field, value in wanted.items():
            assert rows[wanted["wiki"]][field] == value, (field, rows, wanted)
    # Independent expectations for the existing synthetic CP0 fixture, after W2 enrichment.
    details = spark.read.parquet(f"{args.base}/serving/events")
    suspicious = spark.read.parquet(f"{args.base}/serving/suspicious_edits")
    assert details.count() == 7
    risks = {row.event_id: row.risk_score for row in suspicious.select("event_id", "risk_score").collect()}
    assert suspicious.count() == 3
    assert risks == {"fixture-002": 10, "fixture-004": 30, "fixture-005": 20}, risks
    for frame in (details, suspicious):
        assert not {"user", "user_hash", "comment", "raw_payload"} & set(frame.columns)
    trends = spark.read.parquet(f"{args.base}/provisional/trends")
    latest = Window.partitionBy("wiki", "window_start", "page_key").orderBy(F.desc("batch_id"))
    current = trends.withColumn("rn", F.row_number().over(latest)).filter("rn = 1")
    provisional = current.filter("window_start = TIMESTAMP '2026-01-01 00:00:00'")
    finalized = spark.read.parquet(f"{args.base}/gold/trends").filter(
        "window_start = TIMESTAMP '2025-12-31 23:56:00'"
    )
    for frame in (provisional, finalized):
        actual = {row.page_key: row for row in frame.collect()}
        assert set(actual) == {"10", "11"}, actual
        for key, wanted in {"10": (4, 3, 1890, 0.12475), "11": (1, 1, 5, 0.022625)}.items():
            row = actual[key]
            assert (row.edit_count, row.unique_editors, row.abs_byte_delta) == wanted[:3]
            assert math.isclose(row.trend_score, wanted[3], abs_tol=1e-9)
    print(json.dumps({"status": "passed", "counts": counts, "gold_target_rows": len(rows),
                      "events": 7, "suspicious": 3, "trends_provisional_and_finalized": 2}))
finally:
    spark.stop()
