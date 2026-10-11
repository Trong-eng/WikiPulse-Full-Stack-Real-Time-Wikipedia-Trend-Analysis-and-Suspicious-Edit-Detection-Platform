# Activity API — Nhân, tuần 1

CP0 serves the activity rows written by Spark into Cassandra. The API never seeds serving data.

Run `python -m api.app.init_db` to create the configured `CASSANDRA_KEYSPACE` and table.
Initialization retries Cassandra readiness at most 30 times, then exits with an error.
The Compose init service runs this command before the API and Spark services start.

Run `uvicorn api.app.main:app --host 0.0.0.0 --port 8000`. Settings come from the shared
environment configuration. Cassandra connections open during the application lifespan
and close on shutdown; importing the API opens no connection. An unavailable dependency
returns HTTP 503 and can recover when Cassandra returns.

`GET /health` reads Cassandra readiness. `GET /api/v1/activity` accepts an allowlisted
`wiki` (default `enwiki`), an optional timezone-aware ISO `window_start` via `window`,
and `limit` from 1 to 100. The response uses UTC timestamps and labels the activity
counts as provisional. An empty partition returns HTTP 200 with `data: []`.

`GET /api/v1/trends`, `/api/v1/suspicious-edits`, and `/api/v1/events/{event_id}` return
typed HTTP 501 responses identifying the owner, role, and week 2 responsibility.
OpenAPI documentation is available at `/docs`.

Run `.venv/bin/python -m pytest api/tests -q` for the API/store/schema contract tests.
The Cassandra driver connection is the external boundary replaced in unit tests.
The Compose smoke test verifies the real replay-to-Cassandra path.
