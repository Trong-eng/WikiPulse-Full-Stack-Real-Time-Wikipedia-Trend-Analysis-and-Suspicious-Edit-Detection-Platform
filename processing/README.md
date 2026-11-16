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

The shared Compose environment forwards both variables from `.env` or the shell
since W2-TRONG-01. `docker compose run -e NAME=value ...` also overrides them for
a one-off container. Stop the existing Spark instance before starting a replacement;
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

## Week-three HDFS acceptance

Use the shared full profile and overlay described in
[the HDFS README](../storage/hdfs/README.md). Both data and checkpoints must use
HDFS URIs, with a new RUN_ID/serving namespace when migrating from local storage.
Keep the watermark, schema, scoring and sink mode fixed for a checkpoint's lifetime.
Each of the nine query names owns a separate checkpoint; persisted Silver remains
the boundary between deduplication and downstream aggregations.

From the repo root in PowerShell:

```powershell
$env:PYTHONUTF8 = '1'
..\.venv\Scripts\python.exe -m processing.spark.acceptance.run_hdfs
```

This command builds the current Spark/API/replay images, creates a unique Compose
project with random host ports and its own Kafka/Cassandra/HDFS volumes, then
runs the production query starter against real services. It does not change the
developer `.env` or existing data. `--no-build` is only valid after building the
current source; `--keep` retains the test stack for inspection. The default cleans
up only the generated project. Each phase has a 300-second command deadline.

| Phase | Independent expectation |
|---|---|
| initial | UTC midnight fixture, malformed JSON/missing page quarantined, sparse canary only in Bronze; 5 Bronze / 2 Silver, Gold target still empty |
| late | Same ID replayed twice, one with changed timestamp; one distinct late-but-open edit; 8 Bronze / 3 Silver, target count 2 |
| retry_failure | Inject an error **after** a real Cassandra activity upsert succeeds; batch must fail |
| recovered | New JVM resumes the failed batch with the same checkpoint; target activity count 3, never 6; 9 Bronze / 4 Silver |
| finalized | Recreate both HDFS containers retaining volumes; publish clock event advancing watermark; target activity 3 and trend 0.08375 finalize |
| after_restart | Recreate HDFS again; replay an old duplicate, a distinct too-late event and a fresh event; Bronze 13, Silver 6, finalized target unchanged |
| idle_restart | New JVM, no new input; counts and finalized rows unchanged |

Every phase starts a fresh Spark driver; the persistent IDs of all nine queries
must stay equal while their execution run IDs change. Phases drain the Kafka
queries before downstream Silver readers. They also check unique Kafka coordinates
in Bronze, exact Silver IDs, privacy fields, logical key uniqueness, actual HDFS
partition directory paths and UTC partition values, including Gold windows across
midnight. Data and state survive two HDFS container recreations. The separately
stored literal expected results are in `spark/tests/fixtures/week_three_expected.json`.

The fixture intentionally keeps the timestamp-changing duplicate inside the
dedup horizon. IDs are not retained forever: after state eviction, an ID carrying
a sufficiently new timestamp can be treated as a new event. Too-late rows remain
in Bronze but cannot reopen finalized Gold. An idle last window still requires
new event time to advance watermark; wall-clock waiting cannot finalize it.

Evidence is `artifacts/w3-<timestamp>-<id>/report.json`, per-phase logs and
`commands.log`. Failed assertions exit nonzero. The failure injection exists only
in this acceptance module; it does not change the production sink. It proves
activity retry after an uncertain write, not a cross-sink exactly-once transaction.
Analytics Cassandra callbacks and LIVE collection remain their owners' work.

Run the shared UI/API/full-stack regression separately:

```powershell
..\.venv\Scripts\python.exe scripts/smoke_test.py --hdfs
```

See [W3-LINH-01](../docs/plans/W3-LINH-01.md) for results and remaining integration scope.

## Week-three development environment

The standalone lab in `spark/dev/compose.hdfs.yaml` prepares HDFS access for Linh's
tests. It runs one NameNode and one DataNode with replication 1 and separate named
volumes, using the existing `storage/hdfs` XML files. It does not implement the
shared `full` profile or launch Kafka/Cassandra/API. Hadoop daemon startup follows
the [Apache Hadoop 3.4.1 setup](https://hadoop.apache.org/docs/r3.4.1/hadoop-project-dist/hadoop-common/ClusterSetup.html).
The lab formats only a new NameNode volume with no `current/VERSION`.

From the repository root in PowerShell:

```powershell
$lab = 'processing/spark/dev/compose.hdfs.yaml'
docker compose -f $lab config --quiet
docker compose -f $lab pull namenode datanode
docker compose -f $lab build spark
docker compose -f $lab up -d --wait namenode datanode
docker compose -f $lab exec -T namenode hdfs dfsadmin -report
$env:W3_RUN_ID = 'linh-w3-prep-' + (Get-Date -Format 'yyyyMMddHHmmss')
docker compose -f $lab run --rm spark python processing/spark/dev/hdfs_probe.py write
docker compose -f $lab restart namenode datanode
docker compose -f $lab up -d --wait namenode datanode
docker compose -f $lab run --rm spark python processing/spark/dev/hdfs_probe.py read
docker compose -f $lab stop
```

Use the same `W3_RUN_ID` for the write/read pair, and a fresh value for another write.
The probe refuses to overwrite existing output. `stop` retains containers/volumes;
`up -d --wait namenode datanode` starts the lab again. The project is
`wikipulse-linh-w3-lab`, isolated from the application stack. No host ports are
published; Spark accesses `namenode:9000` and the DataNode inside the Docker network.

The probe writes **synthetic environment rows**, reads Parquet partitions through
the Hadoop client, and checks a separate writable checkpoint namespace. It does
not validate production Bronze/Silver/Gold schemas, streaming recovery, late data
or finalized results. Those acceptance steps remain in
[W3-LINH-01](../docs/plans/W3-LINH-01.md). Keep the new HDFS namespace separate from
W1/W2 local output; the default lab Spark command is the environment probe.

On this Windows workspace the existing venv is in the parent directory:

```powershell
..\.venv\Scripts\python.exe -m pip check
..\.venv\Scripts\python.exe -m pytest -q -m 'not integration and not spark'
docker compose -f processing/spark/dev/compose.hdfs.yaml run --rm --no-deps -e HADOOP_CONF_DIR=/tmp/wikipulse-no-hadoop-conf spark python -m pytest processing/spark/tests -q
```

Python/Java/Hadoop for Spark run inside the image. No Windows Hadoop installation,
`winutils.exe`, or host PySpark installation is needed for these commands.
The existing baseline suite writes local `tmp_path` fixtures; disable the lab's
Hadoop configuration for that command so unqualified paths use `file:///`.
The HDFS probe must keep the mounted Hadoop configuration enabled.

## Week-four development environment

Preparation and results are tracked in [W4-LINH-01](../docs/plans/W4-LINH-01.md).
Reuse the existing Python venv and Docker Linux runtime. Start Docker Desktop
before running container commands. Run from the repository root in PowerShell:

```powershell
$env:PYTHONUTF8 = '1'
..\.venv\Scripts\python.exe -m pip check
..\.venv\Scripts\python.exe -m pytest -q -m 'not integration and not spark' --ignore=tests/test_hdfs_bootstrap.py --ignore=tests/test_deployment.py
docker compose -f docker-compose.yml -f docker-compose.hdfs.yml --profile full config --quiet
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/workspace,readonly" -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python wikipulse-spark:0.1.0 -m pytest processing/spark/tests tests/test_hdfs_bootstrap.py -q -p no:cacheprovider
```

The container command mounts the current checkout read-only, so tests use current
source even when the image was built in week three. Test output/state uses container
temporary storage. The image must already exist; on a new machine build it with
`docker compose build spark`. Rebuild when Dockerfile or dependencies change.
Windows excludes the POSIX bootstrap tests (run in the Linux command above) and
deployment tests that use `/dev/null`; Compose configuration validation is separate.

Reuse the week-three acceptance runner for later real Kafka/HDFS/Cassandra activity
regression. Run without `--no-build` to rebuild current source; it creates an isolated
project and cleans up its own volumes. The historical lab and its volumes can remain
stopped until needed. Never run concurrent drivers against the same checkpoints.
Keep analytics in Parquet mode until the W2 Cassandra store is implemented.
Environment preparation and producer tests do not establish group CP3 or LIVE/API
analytics readiness. Week four is for correctness fixes and handoff, with no new
features or contract changes planned.

## Week-four formulas and handoff limits

Default trend score is
`0.50 * min(edit_count / 50, 1) + 0.25 * min(unique_editors / 20, 1) + 0.25 * min(abs_byte_delta / 10000, 1)`.
Only edits enter five-minute windows sliding every minute; windows include their
start and exclude their end. Bots count. Unique editors use Spark's approximate
distinct count of non-null salted hashes (default relative standard deviation
0.05); large populations are estimates. Missing users do not add a distinct editor.
Absolute byte deltas sum magnitudes, so deletion and addition do not cancel; null
deltas contribute nothing, and an all-null group has zero magnitude.

For example, two edits by one editor with total magnitude 40 score **0.0335**.
The W3 finalized target has three edits, three editors and magnitude 650:
`0.03 + 0.0375 + 0.01625 = 0.08375`. Metadata is chosen by descending
`(event_time, event_id, page_title, namespace)` within the stable page key;
arrival order does not choose the title.

Default risk is `min(30 * deletion + 20 * revert + 10 * anonymous_nonbot, 100)`.
Each indicator is either zero or one. Deletion means delta <= -500 (inclusive);
unknown lengths do not trigger deletion. Revert uses the documented anchored
English comment patterns. Anonymous includes temporary accounts. All rules require
an edit. A bot can receive deletion/revert reasons, while the anonymous reason
excludes bots. All three reasons score **60**, or **50** for the equivalent bot;
non-edits score zero. The default rules cannot reach 100; that is a configurable
ceiling. Risk prioritizes review and does not establish vandalism.

Literal W2/W3 expected JSON and [spark/tests/test_week_four.py](spark/tests/test_week_four.py) provide the golden
references. W4 adds combined-rule, bot/non-edit, exact window-boundary and
metadata tie/order checks. Floating point scores use approximate comparisons.
Run results and evidence paths belong in the W4 plan.

Operational limits for handoff:

- Watermark is event time, not wall time. Idle final windows require later valid
  event times to finalize. Late rows cannot reopen finalized Gold.
- Deduplication retains bounded state, not permanent event history. An evicted
  identifier with a sufficiently new timestamp can be accepted again.
- Trend snapshots are absolute totals. Select the greatest completed batch ID per
  key; summing snapshots corrupts counts. Multi-sink writes are not one transaction.
- Activity retry is verified after a real successful upsert followed by failure.
  Analytics Cassandra retry/API and LIVE integration await their module owners.
- HDFS replication 1 and single-node Kafka/Cassandra/Spark are demo infrastructure;
  acceptance establishes persistence/recovery cases, not HA or a production benchmark.
- Rebuild images after source changes for full-stack acceptance. Use fresh isolated
  namespaces after schema/scoring/sink changes; retain configuration throughout a run.

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
