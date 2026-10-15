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
    return f"{wiki}:{page}".encode("utf-8")


def encode_event(line: str, now: datetime, *, source: str = "replay") -> tuple[bytes | None, bytes]:
    """Stamp ingestion metadata without touching source IDs/timestamps.

    Non-object JSON or malformed lines pass through unkeyed so Spark can quarantine them.
    """
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None, line.encode("utf-8")
    if not isinstance(event, dict):
        return None, line.encode("utf-8")
    event["ingested_at"] = now.isoformat()
    event["collector_version"] = collector_version(source)
    return message_key(event), json.dumps(event, ensure_ascii=False).encode("utf-8")
