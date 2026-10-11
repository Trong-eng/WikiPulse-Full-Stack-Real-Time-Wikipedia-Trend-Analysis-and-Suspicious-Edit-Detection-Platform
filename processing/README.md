# Spark CP0 — Linh

The week-one job counts wiki activity in event-time windows of one minute.
Run it with `python -m processing.spark.jobs.streaming_job` inside the Spark image.
The shared `wikipulse_core.config.Settings` supplies runtime configuration.

The entrypoint owns five independent streaming queries and checkpoints:

| Query | Output | Mode |
| --- | --- | --- |
| `bronze_raw` | `<DATA_BASE_PATH>/<RUN_ID>/bronze/raw` | native append Parquet |
| `bronze_invalid` | `<DATA_BASE_PATH>/<RUN_ID>/bronze/invalid` | native append Parquet |
| `silver_events` | `<DATA_BASE_PATH>/<RUN_ID>/silver/events` | native append Parquet |
| `activity_cassandra` | `wiki_activity_by_window` | Update, absolute upserts |
| `activity_gold` | `<DATA_BASE_PATH>/<RUN_ID>/gold/activity` | native append Parquet |

Every checkpoint is `<SPARK_CHECKPOINT_PATH>/<RUN_ID>/<query>`.
Bronze and Silver are partitioned by `event_date/event_hour`; Gold uses
`metric_date/metric_hour/wiki`. The Kafka source starts at `earliest` for a new
checkpoint, fails on offset loss, and limits each trigger to
`MAX_OFFSETS_PER_TRIGGER` (default 1,000). An existing checkpoint resumes offsets.

`spark/wikipulse/transformations.py` owns `RAW_EVENT_SCHEMA` and the explicit
`SILVER_SCHEMA` described in `docs/contracts.md`. Normalization uses Spark
built-in functions. It prioritizes `meta.id`, hashes stable event fields for a
fallback ID, and hashes the salted username. Silver excludes raw usernames,
comments, canary-domain events, and wikis outside `WIKI_ALLOWLIST`. Bronze retains
all Kafka payloads, including canaries and invalid JSON. Invalid rows preserve
the payload, error code, Kafka coordinates, and detection timestamp.

Silver deduplicates by event ID within the configured watermark. Its persisted
Parquet boundary separates deduplication from aggregation. Two independent
activity queries read it with an explicit schema: Cassandra receives provisional
absolute counts, while Gold receives windows only after their event-time
watermark passes. The default watermark is ten minutes. Empty input does not
advance event time, so an idle final window does not finalize by wall clock.

`SPARK_PROGRESS_PATH=/data/progress.json` optionally publishes atomic JSON with
`updated_at`, `active_queries`, and native `lastProgress` values under `queries`.
The values describe the latest batch, rather than cumulative ingestion counts.
The smoke test must wait for its expected provisional counts before publishing
the later fixture phase that advances the watermark.

The driver streams each Cassandra batch through `toLocalIterator()` and
`CassandraActivityStore.upsert_activity()`. Cassandra failures fail the query;
retries overwrite the same absolute counts. Any query failure terminates the
pipeline. SIGINT/SIGTERM and partial startup failures stop queries and close the
driver store and Spark session. This scaffold does not claim exactly-once writes
across all sinks.

Run the real Spark tests with Python 3.11, Java 17, and PySpark 3.5.6:

```sh
docker run --rm -v "$PWD:/workspace" wikipulse-spark:0.1.0 \
  python -m pytest processing/spark/tests -q
```

The suite covers validation, normalization, pseudonymization, canary handling,
activity counts, duplicate/restart behavior, finalized Gold, and driver cleanup.
Trend and suspicious-edit analytics belong to the subsequent weekly checkpoints.
