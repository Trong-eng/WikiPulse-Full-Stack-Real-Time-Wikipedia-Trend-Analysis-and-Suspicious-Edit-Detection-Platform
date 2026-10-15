# Replay producer — Thành

`python -m replay.replay_producer` publishes a JSONL fixture to `KAFKA_RAW_TOPIC`
without rewriting source IDs or event timestamps. It requires `PIPELINE_MODE=REPLAY`.

```bash
docker compose run --rm replay                                   # whole default fixture, 1 s apart
docker compose run --rm replay python -m replay.replay_producer --end 10 --interval 0
docker compose run --rm replay python -m replay.replay_producer --start 10 --interval 0
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--file` | `tests/fixtures/recentchange.jsonl` | JSONL source; must exist |
| `--start` / `--end` | `0` / none | zero-based record range `[start, end)`; blank lines count as records |
| `--interval` | `1.0` | seconds slept after every send, including the last |
| `--speed` | `REPLAY_SPEED_FACTOR` or `1` | divides the interval; only the sending cadence changes |

Sends are synchronous (`acks=all`; a record can block up to ~60 s: 30 s `max_block_ms` plus a
30 s ack wait) so a fixture run is deterministic. The first failed send stops the run; the
`index` in `replay_failed` is the record that failed, so `--start <index>` resumes it (records
sent just before a failure may be duplicated — at-least-once). Files are read as UTF-8 with an
optional BOM.

| Exit | Meaning | Log |
| --- | --- | --- |
| 0 | every selected record acknowledged | `replay_complete events_published=N` |
| 1 | send or flush failed mid-run | `replay_failed reason=send_error index=I sent=N` / `reason=flush_error` |
| 2 | usage: bad flags, speed/interval, range, missing file, mode not REPLAY | argparse error |
| 3 | no broker reachable at startup | `replay_failed reason=broker_unavailable` |

## Envelope

`ingestion/envelope.py` is shared with the week-two LIVE collector:

- payload: source JSON unchanged plus `ingested_at` (ISO UTC) and `collector_version`
  (`replay-<COLLECTOR_VERSION>`, default `replay-0.1.0`; LIVE uses `live-…`). Compose does not
  forward `COLLECTOR_VERSION` yet, so in containers it is always the default;
- key: `wiki:page_id`, falling back to `wiki:title`, then `unknown` for a missing or null part;
- malformed or non-object JSON is sent unchanged and unkeyed so Spark quarantines it in
  `bronze/invalid`; strings that are not valid UTF-8 (lone surrogate escapes) stay `\u`-escaped.

## Limits

Delivery is at-least-once. Replaying the same fixture again re-sends the same IDs; Silver drops
them only within the 10-minute dedup horizon, so a fresh run needs a new `RUN_ID`/namespace
(or `scripts/smoke_test.py`). `tests/fixtures/recentchange.jsonl` and
`expected_activity.json` are the CP0 contract: don't change their rows without updating the smoke
expectations with Linh and Trọng.
