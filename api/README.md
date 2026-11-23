# Serving API — Nhân

The API serves the rows Spark writes into Cassandra. It never seeds serving data.

Run `python -m api.app.init_db` to create the configured `CASSANDRA_KEYSPACE` and tables.
Initialization retries Cassandra readiness at most 30 times, then exits with an error.
The Compose init service runs this command before the API and Spark services start.

Run `uvicorn api.app.main:app --host 0.0.0.0 --port 8000`. Settings come from the shared
environment configuration. Cassandra connections open during the application lifespan
and close on shutdown; importing the API opens no connection. An unavailable dependency
returns HTTP 503 and can recover when Cassandra returns.

| Endpoint | Query parameters |
|---|---|
| `GET /health` | — (503 while Cassandra is not ready) |
| `GET /api/v1/activity` | `wiki`, `window` (window_start), `limit` 1–100 |
| `GET /api/v1/trends` | `wiki`, `window` (5-minute window_start; latest when omitted), `limit` 1–100 |
| `GET /api/v1/suspicious-edits` | `wiki`, `window`, `minutes` 1–15 (default 5), `min_score` 0–100, `limit` 1–100 |
| `GET /api/v1/events/{event_id}` | — (404 `EVENT_NOT_FOUND` when absent) |

`wiki` defaults to `enwiki` and must be in `WIKI_ALLOWLIST`; `window` must carry a timezone.
Responses use UTC timestamps. Empty results return HTTP 200 with `data: []`. Every error is
`{"detail": {"code", "message", ...}}`: 422 `INVALID_QUERY` (with `fields`), 404
`EVENT_NOT_FOUND`, 503 `DEPENDENCY_UNAVAILABLE` (with `source`) or 503 `CAPACITY_EXCEEDED`.
Payloads are specified in `docs/contracts.md`; OpenAPI is at `/docs`. The published schema
is committed as `api/openapi.json`; a regression test fails when the app drifts from it.
After an intended change, regenerate it in the same PR as the contract update:
`UPDATE_OPENAPI=1 .venv/bin/python -m pytest api/tests/test_regression.py`.

Trends, suspicious edits and event detail have rows only when Spark runs with
`SPARK_ANALYTICS_SINK=cassandra`; with the default `parquet` they return empty data and 404.

Run `.venv/bin/python -m pytest api/tests -q` for the API/store/schema contract tests.
The Cassandra driver connection is the external boundary replaced in unit tests. Tests
marked `integration` run against a real node:

```bash
docker run -d --name wikipulse-it -p 127.0.0.1:19042:9042 cassandra:4.1.8
CASSANDRA_IT_HOST=127.0.0.1 CASSANDRA_IT_PORT=19042 .venv/bin/python -m pytest -m integration api/tests
```

## Runbook

Host port `API_HOST_PORT` (default 18000 on the dev machine). Commands run from the repo root.

| Symptom | Check | Action |
|---|---|---|
| `/health` 503, every endpoint 503 `DEPENDENCY_UNAVAILABLE` | `docker compose ps cassandra`, `docker compose logs api` | Wait for Cassandra health; the API recovers by itself, no restart needed |
| Trends/suspicious always `data: []`, events 404 | `docker compose exec spark cat /data/progress.json` lists `trends_cassandra` | Spark runs with `SPARK_ANALYTICS_SINK=parquet`; set `cassandra` and restart Spark with a new `RUN_ID` |
| 503 `CAPACITY_EXCEEDED` | partition size, see `storage/cassandra/README.md` | Narrow `minutes`; a trend window above 5,000 pages needs a schema change (not MVP) |
| Event detail 404 for a known id | event older than 7 days | Expected (TTL); history stays in Bronze/Silver |
| 422 `INVALID_QUERY` | `detail.fields` names the parameter | Fix the request; `window` needs a timezone such as `Z` |
| Spark query fails with `ValidationError` from the store | `docker compose logs spark` | A row breaks contract v0.2; fix the producer, never relax the store |

Quick checks:

```bash
curl -s localhost:18000/health
curl -s "localhost:18000/api/v1/trends?wiki=enwiki&limit=5"
curl -s "localhost:18000/api/v1/suspicious-edits?wiki=enwiki&minutes=15&min_score=20"
```

Never fix a bad run by deleting Spark checkpoints or truncating serving tables; start a new
`RUN_ID` with a new `CASSANDRA_KEYSPACE` (`python -m api.app.init_db` creates it).
