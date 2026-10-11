"""Inspect actual streaming Parquet output inside the Spark image."""

import argparse
import json

from pyspark.sql import SparkSession

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
    print(json.dumps({"status": "passed", "counts": counts, "gold_target_rows": len(rows)}))
finally:
    spark.stop()
