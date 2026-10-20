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

## Week-one verification

From the repository root, build the current source before running the suite.
Compose copies the source into the image; editing a local test does not update
an already built image.

```sh
docker compose build spark
docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q --capture=tee-sys
```

The additional contract checks exercise:

- UTC conversion across date boundaries, millisecond precision, source-time
  priority, epoch fallback, and UTC Parquet partitions.
- Mixed valid/invalid batches, nullable fields, title-only/page-ID-only events,
  and ingestion-time fallback to the Kafka timestamp.
- Empty source IDs, stable fallback IDs for equivalent instants, distinct event
  identities, and source-ID priority.
- Salt-dependent user hashes and Silver Parquet round trips without raw user,
  comment, or payload columns.
- Minute boundaries, wiki isolation, event-type counters, and the flattened
  activity schema consumed by the Cassandra writer.

To inspect the pseudonymized LIVE fixture through the actual Spark parser,
normalizer and activity aggregation:

```sh
docker compose run --rm --no-deps spark python -m pytest processing/spark/tests/test_transformations.py -q -k live_sample --capture=tee-sys
```

This test reads `tests/fixtures/recentchange_live_sample.jsonl` from disk. It
checks accepted IDs, title-based events with no `page_id`, millisecond timestamps,
nullable fields, pseudonymization, and independently specified activity totals.
`LIVE_SAMPLE_REPORT=` prints aggregate counts and observations for the pending
backlog items, without usernames, hashes, titles, or raw payloads. Missing-user
observations use two synthetic events because the LIVE fixture does not contain
that case. Observations are diagnostics; test success does not resolve them.

## Known LIVE limitations

See [the Linh backlog](../docs/backlog.md#linh) for the tracked findings:

- **BL-THANH-19:** temporary accounts are not recognized by the current
  `anon`/IP-based detection, so anonymous edit counts can be understated.
- **BL-THANH-20:** a sparse canary with only schema/meta is kept in Bronze and
  excluded from Silver, but also enters invalid quarantine as `MISSING_WIKI`.
- **BL-THANH-21:** absent/null users currently receive the same non-null salted
  hash. It must not be treated as evidence of a shared editor identity.

The fixes and any consumer-facing changes need the reviews recorded in
[the week-one plan](../docs/plans/W1-LINH-01.md). The current activity code counts
valid `categorize`/`log` events in `event_count`; the edit counters count only
`type=edit`, and `new_page_count` counts `type=new`. Display semantics are tracked
in [BL-THANH-05](../docs/backlog.md#cần-nhóm-quyết-định).
Canonical interface definitions remain in [contracts](../docs/contracts.md);
run results and reviewer handoff remain in the week-one plan.
