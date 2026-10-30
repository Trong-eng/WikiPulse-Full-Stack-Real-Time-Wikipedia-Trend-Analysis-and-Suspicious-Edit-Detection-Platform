# Spark activity và analytics — Linh

The week-one job counts wiki activity in event-time windows of one minute.
Run it with `python -m processing.spark.jobs.streaming_job` inside the Spark image.
The shared `wikipulse_core.config.Settings` supplies runtime configuration.

The entrypoint owns nine independent streaming queries and checkpoints. Five
preserve activity/CP0; four implement the week-two analytics outputs:

| Query | Output | Mode |
| --- | --- | --- |
| `bronze_raw` | `<DATA_BASE_PATH>/<RUN_ID>/bronze/raw` | native append Parquet |
| `bronze_invalid` | `<DATA_BASE_PATH>/<RUN_ID>/bronze/invalid` | native append Parquet |
| `silver_events` | `<DATA_BASE_PATH>/<RUN_ID>/silver/events` | native append Parquet |
| `activity_cassandra` | `wiki_activity_by_window` | Update, absolute upserts |
| `activity_gold` | `<DATA_BASE_PATH>/<RUN_ID>/gold/activity` | native append Parquet |
| `trends_provisional_parquet` | `<DATA_BASE_PATH>/<RUN_ID>/provisional/trends/batch_id=<N>` | Update, absolute changelog |
| `suspicious_parquet` | `<DATA_BASE_PATH>/<RUN_ID>/serving/suspicious_edits` | native append Parquet |
| `events_parquet` | `<DATA_BASE_PATH>/<RUN_ID>/serving/events` | native append Parquet |
| `trends_gold` | `<DATA_BASE_PATH>/<RUN_ID>/gold/trends` | native append Parquet, finalized |

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
activity counts, duplicate/restart behavior, finalized Gold, and driver cleanup,
plus the week-two analytics contract and streaming tests below.

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
that case. These observations are diagnostics; the separate week-two regression
tests assert the corrected behavior for temporary accounts, canaries and missing users.

## Week-two analytics

The interface and exact rule semantics are in [contracts v0.2](../docs/contracts.md#tuần-2--trends-suspicious-edits-event-detail-v02).
Silver now adds `is_revert`; temporary accounts count as anonymous, missing/null/
blank users have a null hash, and sparse canaries stay in Bronze without entering
invalid quarantine. Comment text is used transiently to derive `is_revert` and is
discarded before Silver. Revert recognition currently covers the documented English
patterns; risk scores prioritize review and do not establish vandalism.

Trends consume only edits (including bots), in five-minute event-time windows
sliding every minute. Unique editors use `approx_count_distinct` excluding nulls;
byte magnitude sums absolute deltas, with zero for all-null groups. Scoring uses
fixed caps, not microbatch min/max. A deterministic latest metadata aggregate keeps
one row per stable page key. Event detail covers every Silver event; suspicious
output contains only edits with positive risk. Unknown length does not imply a
deletion, and bots do not receive the anonymous-edit reason.

`config/scoring.yaml` is loaded once at startup through `yaml.safe_load`. Invalid
keys, nonfinite/negative weights, weights not summing to 1, nonpositive caps or
thresholds, noninteger risk weights and max_score outside 1–100 fail before queries
start. PyYAML is pinned in `spark/requirements-scoring.txt` and installed by the
Spark Dockerfile. To run scoring tests on the host, install that requirements file;
the standard lightweight suite does not require PyYAML.

Container environment (module-owned, independent of shared Settings):

| Variable | Default | Meaning |
|---|---|---|
| `SPARK_SCORING_PATH` | Repository `config/scoring.yaml` | Read-only scoring file, fixed for the run |
| `SPARK_ANALYTICS_SINK` | `parquet` | `parquet` for producer handoff, `cassandra` for an implemented W2 store |

Pass these into the container explicitly (`docker compose run -e NAME=value ...`
or a Compose override). The shared Compose environment does not yet forward these
two names from `.env`. Stop the existing Spark instance before starting a replacement;
never run two drivers with the same checkpoints. Standard Python exceptions cause
nonzero exit; missing Cassandra W2 methods fail startup with their names.

**Schema/config changes require a fresh RUN_ID, data/checkpoint namespace and an
isolated serving namespace.** Use `PIPELINE_VERSION=0.2.0` for a W2 run. Never reuse
v0.1 Silver/checkpoints or change scoring/sink mode partway through a run. Activity
and its Cassandra path remain active in both analytics modes.

Parquet mode is the runnable producer boundary while Nhân implements W2 Cassandra.
Trend updates are written under `batch_id=<N>`; retry overwrites the same batch
directory. Wait for `_SUCCESS` before reading a batch. These files are a changelog:
keep the greatest batch_id per `(wiki, window_start, page_key)` across batches,
not just the last directory, and never sum snapshots. This file handoff is not an
atomic multi-sink transaction or a replacement for Cassandra/API serving.
Suspicious/event outputs are native append streams from deduplicated Silver.
Gold trends uses the same formula but emits finalized windows after watermark;
an idle last window does not finalize by wall clock.

In Cassandra mode, inject/implement a store with `upsert_trends`,
`upsert_suspicious_edits`, `upsert_events` as well as the existing activity method.
The default `CassandraActivityStore` currently lacks these W2 methods and will fail
validation in this mode. Four query names become `trends_cassandra`,
`suspicious_cassandra`, `events_cassandra`, `trends_gold`; their checkpoints remain
independent. Row adapters stream UTC dictionary values through `toLocalIterator`;
store errors fail the query, and retries resend absolute totals.

Golden input/expected files are in `spark/tests/fixtures/week_two*`. The tests
cover five overlapping windows, threshold edges, null/bot/temporary accounts,
caps, stable page keys, all four output queries, late-but-open updates, checkpoint
restart and finalized windows rejecting too-late data:

```sh
docker compose build spark
docker compose run --rm --no-deps spark python -m pytest processing/spark/tests -q
```

## LIVE integration status

See [the Linh backlog](../docs/backlog.md#linh) for the tracked findings:

- **BL-THANH-19/20/21:** addressed in the week-two producer with regression tests.
- LIVE collector, Cassandra W2 tables/store/API and dashboard integration remain
  their respective owners' tasks; producer tests do not claim these are complete.

Evidence and remaining integration tasks are in
[the week-two plan](../docs/plans/W2-LINH-01.md). The current activity code counts
valid `categorize`/`log` events in `event_count`; the edit counters count only
`type=edit`, and `new_page_count` counts `type=new`. Display semantics are tracked
in [BL-THANH-05](../docs/backlog.md#cần-nhóm-quyết-định).
Canonical interface definitions remain in [contracts](../docs/contracts.md);
run results and reviewer handoff remain in the corresponding weekly plans.
