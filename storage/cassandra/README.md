# Cassandra activity serving — Nhân

`schema.cql` is a template consumed by `python -m api.app.init_db`; the validated
`CASSANDRA_KEYSPACE` replaces `__KEYSPACE__`. The init command uses the API image.

`wiki_activity_by_window` partitions by wiki and clusters by `window_start DESC`.
Activity writes contain absolute totals, so replaying a Spark batch replaces the same
row at `(wiki, window_start)`. Reads use a single wiki partition or an exact
`window_start`; no `ALLOW FILTERING` or mutable score appears in a key.

The week 1 layout supports low-volume replay. TTL, retention, partition capacity,
trends, suspicious edits, and event detail remain owned work in later weeks.
