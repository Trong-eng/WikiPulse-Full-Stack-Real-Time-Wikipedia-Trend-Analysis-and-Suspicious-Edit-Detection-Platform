# Cassandra serving — Nhân

`schema.cql` is a template consumed by `python -m api.app.init_db`; the validated
`CASSANDRA_KEYSPACE` replaces `__KEYSPACE__` and `--` comment lines are dropped. Every
statement is `IF NOT EXISTS`, so re-running init on an existing keyspace is safe. The init
command uses the API image.

| Table | Primary key | Written by |
|---|---|---|
| `wiki_activity_by_window` | `((wiki), window_start)` DESC | `upsert_activity` |
| `page_trends_by_window` | `((wiki, window_start), page_key)` | `upsert_trends` |
| `trend_windows_by_wiki` | `((wiki), window_start)` DESC | `upsert_trends`, after the rows |
| `suspicious_edits_by_bucket` | `((wiki, bucket_start), event_id)` | `upsert_suspicious_edits` |
| `suspicious_buckets_by_wiki` | `((wiki), bucket_start)` DESC | `upsert_suspicious_edits`, after the rows |
| `events_by_id` | `(event_id)`, TTL 7 days | `upsert_events` |

All writes are absolute values on stable keys, so a retried Spark batch rewrites the same
rows. Index tables are written after the data rows of a batch: a reader that sees a window
in the index finds its rows. Reads always restrict the full partition key; there is no
`ALLOW FILTERING` and no score in a key. Top-N reads at most 5,000 rows (one trend
partition, or the sum of the suspicious buckets requested) and fails with
`CapacityExceeded` instead of returning a truncated ranking.

Spark writes trends/suspicious/event rows here only with `SPARK_ANALYTICS_SINK=cassandra`;
the Compose default is still `parquet` (see `processing/README.md`).

## Inspecting data

```bash
docker compose exec cassandra cqlsh -e "
  SELECT window_start FROM wikipulse.trend_windows_by_wiki WHERE wiki = 'enwiki' LIMIT 3;
  SELECT count(*) FROM wikipulse.page_trends_by_window
    WHERE wiki = 'enwiki' AND window_start = '2026-01-01 00:00:00+0000';
  SELECT event_id, risk_score, TTL(wiki) FROM wikipulse.events_by_id WHERE event_id = 'fixture-004';"
```

Every query restricts a full partition key; if a query needs `ALLOW FILTERING`, it is the
wrong table. Partition sizes: `docker compose exec cassandra nodetool tablestats wikipulse`
("Compacted partition maximum bytes"). `schema.cql` columns are checked against the store
models by `api/tests/test_regression.py`.

## Capacity measurement

`measure_capacity.py` writes synthetic contract v0.2 rows into a throwaway keyspace,
flushes, reads `nodetool tablestats` and drops the keyspace:

```bash
docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8
PYTHONPATH=. .venv/bin/python storage/cassandra/measure_capacity.py \
    --host 127.0.0.1 --port 19042 --container wikipulse-it --rows 20000
docker rm -f wikipulse-it
```

Results and the TTL decision are recorded in `docs/plans/W3-NHAN-01.md`.
