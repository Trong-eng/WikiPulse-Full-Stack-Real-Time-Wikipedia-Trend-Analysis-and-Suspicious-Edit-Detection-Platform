"""Supervise all queries as one pipeline and expose bounded smoke progress."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def publish_progress(path, queries):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "queries": {query.name: query.lastProgress for query in queries},
        "active_queries": {query.name: query.isActive for query in queries},
    }
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(destination)


def supervise_queries(spark, queries, shutdown, progress_path=None):
    while not shutdown.is_set():
        # awaitAnyTermination propagates a Spark query exception immediately.
        spark.streams.awaitAnyTermination(1)
        if shutdown.is_set():
            return
        for query in queries:
            failure = query.exception()
            if failure is not None:
                raise RuntimeError(f"Streaming query {query.name} failed") from failure
            if not query.isActive:
                raise RuntimeError(f"Streaming query {query.name} terminated unexpectedly")
        if progress_path:
            publish_progress(progress_path, queries)


def close_pipeline(queries, store, spark):
    """Stop readers before writers and preserve the original failure during cleanup."""
    for query in reversed(queries):
        try:
            if query.isActive:
                query.stop()
        except Exception:
            LOGGER.exception("Failed to stop query %s", query.name)
    for resource, method in ((store, "close"), (spark, "stop")):
        if resource is not None:
            try:
                getattr(resource, method)()
            except Exception:
                LOGGER.exception("Failed to close %s", type(resource).__name__)
