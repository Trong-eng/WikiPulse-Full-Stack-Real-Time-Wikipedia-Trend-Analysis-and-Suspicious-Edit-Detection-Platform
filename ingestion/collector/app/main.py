"""Điểm vào collector LIVE của Thành."""

import argparse
import logging
import os
import signal
import sys
import threading
from pathlib import Path

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError
from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging

from ingestion.collector.app.collector import (
    Collector,
    PermanentStreamError,
    PublishFailure,
    run_collector,
)
from ingestion.collector.app.recording import Recorder, RecordingError

logger = logging.getLogger(__name__)
DEFAULT_URL = "https://stream.wikimedia.org/v2/stream/recentchange"


def main(argv=()):
    configure_logging("collector")
    parser = argparse.ArgumentParser(description="Collect LIVE recent changes")
    parser.add_argument("--record", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    root = Path(__file__).resolve().parents[3]
    record_root = root / "artifacts" / "recordings"
    if args.record is not None:
        try:
            record_root.resolve().relative_to(root)
            args.record.resolve().relative_to(record_root.resolve())
        except (ValueError, OSError):
            logger.error("invalid_record_path")
            return 2
    try:
        settings = Settings.from_env()
    except (TypeError, ValueError):
        logger.error("invalid_configuration")
        return 2
    if settings.pipeline_mode != "LIVE":
        logger.error("collector_requires_live_mode")
        return 2
    url = os.environ.get("WIKIMEDIA_STREAM_URL", DEFAULT_URL)
    if not url.startswith(("http://", "https://")):
        logger.error("invalid_stream_url")
        return 2
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda _signum, _frame: stop.set())
    try:
        producer = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers,
                                 acks="all", retries=5, max_block_ms=1000)
    except KafkaError:
        logger.error("kafka_unavailable")
        return 3
    try:
        recorder = Recorder(args.record, record_root) if args.record is not None else None
    except RecordingError:
        logger.error("recording_create_failed")
        producer.close(timeout=5)
        return 2
    collector = Collector(producer, settings.kafka_raw_topic, recorder=recorder)
    result = 0
    try:
        with requests.Session() as session:
            run_collector(collector, session, url, stop)
    except PermanentStreamError:
        logger.error("stream_rejected")
        result = 2
    except PublishFailure:
        logger.error("kafka_unconfirmed_on_shutdown")
        result = 1
    except RecordingError:
        logger.error("recording_failed")
        result = 1
    finally:
        try:
            producer.flush(timeout=30)
            collector.poll()
            if collector.acks.pending:
                result = 1
        except KafkaError:
            result = 1
            logger.error("kafka_flush_failed")
        except Exception:
            result = 1
            logger.error("kafka_ack_failed")
        finally:
            try:
                producer.close(timeout=30)
            except Exception:
                result = 1
                logger.error("kafka_close_failed")
            if recorder is not None:
                try:
                    recorder.close()
                except RecordingError:
                    result = 1
                    logger.error("recording_close_failed")
            collector.log_counters()
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
