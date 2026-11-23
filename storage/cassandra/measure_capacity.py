"""Measure on-disk bytes per serving row on a throwaway keyspace (W3-NHAN-01).

    PYTHONPATH=. python storage/cassandra/measure_capacity.py --host 127.0.0.1 --port 19042 \
        --container wikipulse-it --rows 20000

Writes synthetic rows shaped like contract v0.2 through the real store, flushes,
reads `nodetool tablestats`, then drops the keyspace. No real user data is used.
"""

import argparse
import json
import re
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone

from wikipulse_core.config import Settings
from wikipulse_core.serving import CassandraActivityStore, Cluster

from api.app.init_db import initialize_database

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def events(count):
    for n in range(count):
        at = T0 + timedelta(seconds=n)
        yield {
            "event_id": f"{uuid.uuid4()}", "wiki": "enwiki", "event_time": at,
            "page_key": str(100000 + n % 5000), "page_title": f"Synthetic page {n % 5000}",
            "namespace": 0, "event_type": "edit", "revision_old": 10**9 + n,
            "revision_new": 10**9 + n + 1, "length_old": 20000, "length_new": 19800,
            "byte_delta": -200, "is_anonymous": n % 9 == 0, "is_bot": n % 13 == 0,
            "is_minor": False, "risk_score": 10 if n % 9 == 0 else 0,
            "risk_reasons": ["ANONYMOUS_EDIT"] if n % 9 == 0 else [],
            "pipeline_version": "0.2.0", "processed_at": at + timedelta(seconds=5),
        }


def trends(count):
    for n in range(count):
        yield {
            "wiki": "enwiki", "page_key": str(100000 + n), "page_title": f"Synthetic page {n}",
            "namespace": 0, "window_start": T0, "window_end": T0 + timedelta(minutes=5),
            "edit_count": 3, "unique_editors": 2, "abs_byte_delta": 900, "trend_score": 0.1,
            "updated_at": T0 + timedelta(minutes=6),
        }


def live_bytes(container, keyspace, table):
    subprocess.run(["docker", "exec", container, "nodetool", "flush", keyspace, table], check=True)
    output = subprocess.run(
        ["docker", "exec", container, "nodetool", "tablestats", f"{keyspace}.{table}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return int(re.search(r"Space used \(live\): (\d+)", output).group(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19042)
    parser.add_argument("--container", required=True, help="Docker container running Cassandra")
    parser.add_argument("--rows", type=int, default=20000)
    args = parser.parse_args()
    keyspace = f"wikipulse_cap_{uuid.uuid4().hex[:8]}"
    settings = Settings(cassandra_host=args.host, cassandra_port=args.port,
                        cassandra_keyspace=keyspace)
    initialize_database(settings, max_attempts=3, retry_delay=1)
    store = CassandraActivityStore(settings)
    try:
        report = {"rows": args.rows}
        for table, writer, rows in (
            ("events_by_id", store.upsert_events, events(args.rows)),
            ("page_trends_by_window", store.upsert_trends, trends(min(args.rows, 5000))),
        ):
            started = time.monotonic()
            writer(rows)
            seconds = time.monotonic() - started
            written = args.rows if table == "events_by_id" else min(args.rows, 5000)
            size = live_bytes(args.container, keyspace, table)
            report[table] = {"rows": written, "bytes": size,
                             "bytes_per_row": round(size / written, 1),
                             "rows_per_second": round(written / seconds)}
        started = time.monotonic()
        store.get_trends("enwiki", limit=20)
        report["page_trends_by_window"]["top20_read_ms"] = round(
            (time.monotonic() - started) * 1000
        )
        print(json.dumps(report, indent=2))
    finally:
        store.close()
        cluster = Cluster([args.host], port=args.port)
        try:
            cluster.connect().execute(f"DROP KEYSPACE IF EXISTS {keyspace}")
        finally:
            cluster.shutdown()


if __name__ == "__main__":
    main()
