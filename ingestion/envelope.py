"""Kafka envelope shared by replay and the LIVE collector (docs/contracts.md, Kafka)."""

import json
import os
from datetime import datetime


def collector_version(source: str) -> str:
    return f"{source}-{os.getenv('COLLECTOR_VERSION', '0.1.0')}"


def message_key(event: dict) -> bytes:
    wiki = event.get("wiki") or "unknown"
    page = event.get("page_id")
    if page is None:
        page = event.get("title") or "unknown"
    # backslashreplace: a lone surrogate in a title must not crash keying.
    return f"{wiki}:{page}".encode("utf-8", "backslashreplace")


def encode_event(line: str, now: datetime, *, source: str = "replay") -> tuple[bytes | None, bytes]:
    """Stamp ingestion metadata without touching source IDs/timestamps.

    Malformed or non-object JSON passes through unkeyed so Spark can quarantine it. Strings
    that are not valid UTF-8 (lone surrogate escapes) stay \\u-escaped in the payload.
    """
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None, line.encode("utf-8")
    if not isinstance(event, dict):
        return None, line.encode("utf-8")
    event["ingested_at"] = now.isoformat()
    event["collector_version"] = collector_version(source)
    try:
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        payload = json.dumps(event).encode("utf-8")
    return message_key(event), payload
