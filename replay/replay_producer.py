"""Publish fixture JSONL records without rewriting source timestamps or identifiers."""

import argparse
import logging
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging

from ingestion.envelope import encode_event, message_key

__all__ = ["encode_event", "message_key", "replay_delay", "main"]

logger = logging.getLogger(__name__)


def replay_delay(interval: float, speed: float) -> float:
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("REPLAY_SPEED_FACTOR must be finite and positive")
    if not math.isfinite(interval) or interval < 0:
        raise ValueError("interval must be finite and non-negative")
    return interval / speed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("tests/fixtures/recentchange.jsonl"))
    parser.add_argument("--start", type=int, default=0, help="Zero-based inclusive record index")
    parser.add_argument("--end", type=int, default=None, help="Zero-based exclusive record index")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--speed", type=float, default=float(os.getenv("REPLAY_SPEED_FACTOR", "1")))
    args = parser.parse_args()
    delay = replay_delay(args.interval, args.speed)
    settings = Settings.from_env()
    if settings.pipeline_mode != "REPLAY":
        parser.error("replay requires PIPELINE_MODE=REPLAY; use an isolated run from LIVE")
    if args.start < 0 or (args.end is not None and args.end <= args.start):
        parser.error("--start/--end must select a non-empty forward range")
    configure_logging("replay")
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        acks="all", retries=5, max_block_ms=30000,
    )
    sent = 0
    try:
        with args.file.open(encoding="utf-8") as source:
            for index, line in enumerate(source):
                if index < args.start:
                    continue
                if args.end is not None and index >= args.end:
                    break
                if not line.strip():
                    continue
                key, value = encode_event(line.strip(), datetime.now(timezone.utc))
                producer.send(settings.kafka_raw_topic, key=key, value=value).get(timeout=30)
                sent += 1
                logger.info("event_published index=%s topic=%s", index, settings.kafka_raw_topic)
                if delay:
                    time.sleep(delay)
        producer.flush(timeout=30)
        logger.info("replay_complete events_published=%s mode=REPLAY", sent)
    finally:
        producer.close(timeout=30)


if __name__ == "__main__":
    main()
