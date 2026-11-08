"""Check lab connectivity/persistence; this is not pipeline acceptance evidence."""

import argparse
import json
import os
import re
from datetime import date

from pyspark.sql import SparkSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "read"))
    args = parser.parse_args()
    run_id = os.environ["RUN_ID"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError("RUN_ID must be a safe directory identifier")
    base = f"hdfs://namenode:9000/wikipulse/{run_id}/environment_probe"
    checkpoint = f"hdfs://namenode:9000/checkpoints/{run_id}/environment_probe"
    spark = (
        SparkSession.builder.master("local[2]")
        .appName("WikiPulse W3 environment probe")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    try:
        # Synthetic rows deliberately do not pretend to be the production schemas.
        df = spark.createDataFrame(
            [(1, date(2026, 11, 4), 0, "enwiki"), (2, date(2026, 11, 4), 1, "viwiki")],
            "id long, event_date date, event_hour int, wiki string",
        )
        for layer in ("bronze", "silver", "gold"):
            path = f"{base}/{layer}"
            if args.mode == "write":
                df.write.mode("errorifexists").partitionBy("event_date", "event_hour").parquet(path)
            actual = spark.read.parquet(path)
            rows = {(r.id, str(r.event_date), r.event_hour, r.wiki) for r in actual.collect()}
            assert rows == {(1, "2026-11-04", 0, "enwiki"), (2, "2026-11-04", 1, "viwiki")}
        # Check the separate checkpoint namespace is writable; streaming recovery is W3 work.
        if args.mode == "write":
            spark.createDataFrame([("probe-only",)], "value string").write.text(checkpoint)
        assert spark.read.text(checkpoint).first().value == "probe-only"
        print("HDFS_ENVIRONMENT_PROBE=" + json.dumps({
            "status": "passed", "mode": args.mode, "run_id": run_id,
            "spark": spark.version,
            "hadoop_client": spark._jvm.org.apache.hadoop.util.VersionInfo.getVersion(),
            "rows_per_layer": 2, "data_uri": base, "checkpoint_probe_uri": checkpoint,
            "scope": "environment only; not pipeline or streaming checkpoint acceptance",
        }, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
