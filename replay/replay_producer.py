"""Publish fixture JSONL records without rewriting source timestamps or identifiers."""

import argparse
import logging
import math
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging

from ingestion.envelope import encode_event, message_key

__all__ = ["ReplaySendError", "ReplayStats", "encode_event", "main", "message_key",
           "replay_delay", "run_replay"]

# 2 is also what argparse uses for usage errors.
EXIT_OK, EXIT_SEND_FAILED, EXIT_USAGE, EXIT_BROKER_UNAVAILABLE = 0, 1, 2, 3

logger = logging.getLogger(__name__)


@dataclass
class ReplayStats:
    sent: int = 0
    skipped_blank: int = 0
    last_index: int | None = None


class ReplaySendError(RuntimeError):
    def __init__(self, index: int, stats: ReplayStats):
        super().__init__(f"send failed at record index {index} after {stats.sent} sent")
        self.index = index
        self.stats = stats


def replay_delay(interval: float, speed: float) -> float:
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("REPLAY_SPEED_FACTOR must be finite and positive")
    if not math.isfinite(interval) or interval < 0:
        raise ValueError("interval must be finite and non-negative")
    return interval / speed


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_replay(
    lines: Iterable[str],
    send: Callable[[bytes | None, bytes], None],
    *,
    start: int = 0,
    end: int | None = None,
    delay: float = 0.0,
    now: Callable[[], datetime] = _utc_now,
    sleep: Callable[[float], None] = time.sleep,
) -> ReplayStats:
    """Send lines [start, end) in order; stop at the first failed send.

    Blank lines are skipped but still count as record indexes. `delay` follows every send,
    including the last one, so speed only changes the sending cadence.
    """
    stats = ReplayStats()
    for index, line in enumerate(lines):
        if index < start:
            continue
        if end is not None and index >= end:
            break
        if not line.strip():
            stats.skipped_blank += 1
            continue
        key, value = encode_event(line.strip(), now())
        try:
            send(key, value)
        except Exception as exc:  # any producer failure ends the run; caller maps the exit code
            raise ReplaySendError(index, stats) from exc
        stats.sent += 1
        stats.last_index = index
        logger.info("event_published index=%s", index)
        if delay:
            sleep(delay)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("tests/fixtures/recentchange.jsonl"))
    parser.add_argument("--start", type=int, default=0, help="Zero-based inclusive record index")
    parser.add_argument("--end", type=int, default=None, help="Zero-based exclusive record index")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--speed", type=float, default=float(os.getenv("REPLAY_SPEED_FACTOR", "1")))
    args = parser.parse_args()
    try:
        delay = replay_delay(args.interval, args.speed)
    except ValueError as exc:
        parser.error(str(exc))
    settings = Settings.from_env()
    if settings.pipeline_mode != "REPLAY":
        parser.error("replay requires PIPELINE_MODE=REPLAY; use an isolated run from LIVE")
    if args.start < 0 or (args.end is not None and args.end <= args.start):
        parser.error("--start/--end must select a non-empty forward range")
    if not args.file.is_file():
        parser.error(f"--file {args.file} does not exist")
    configure_logging("replay")
    from kafka import KafkaProducer
    from kafka.errors import KafkaError, NoBrokersAvailable

    try:
        producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            acks="all", retries=5, max_block_ms=30000,
        )
    except NoBrokersAvailable:
        logger.error("replay_failed reason=broker_unavailable bootstrap=%s",
                     settings.kafka_bootstrap_servers)
        raise SystemExit(EXIT_BROKER_UNAVAILABLE)

    topic = settings.kafka_raw_topic
    failed = False
    try:
        # utf-8-sig: Windows tools (PowerShell Out-File) write a BOM that would corrupt record 0.
        with args.file.open(encoding="utf-8-sig") as source:
            stats = run_replay(
                source,
                lambda key, value: producer.send(topic, key=key, value=value).get(timeout=30),
                start=args.start, end=args.end, delay=delay,
            )
        producer.flush(timeout=30)
    except ReplaySendError as exc:
        failed = True
        logger.error("replay_failed reason=send_error index=%s sent=%s topic=%s error=%r",
                     exc.index, exc.stats.sent, topic, exc.__cause__)
        raise SystemExit(EXIT_SEND_FAILED)
    except KafkaError as exc:
        failed = True
        logger.error("replay_failed reason=flush_error sent=%s topic=%s error=%r",
                     stats.sent, topic, exc)
        raise SystemExit(EXIT_SEND_FAILED)
    finally:
        try:
            # A dead broker leaves batches pending; don't let close() replace the exit code.
            producer.close(timeout=5 if failed else 30)
        except Exception:
            logger.warning("producer_close_failed", exc_info=True)
    logger.info("replay_complete events_published=%s mode=REPLAY topic=%s", stats.sent, topic)


if __name__ == "__main__":
    main()
