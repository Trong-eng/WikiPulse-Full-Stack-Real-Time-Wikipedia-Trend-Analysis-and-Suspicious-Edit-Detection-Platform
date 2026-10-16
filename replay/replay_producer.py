"""Replay producer: đọc file JSONL và gửi từng dòng vào Kafka raw topic theo đúng thứ tự.

Đây là nguồn dữ liệu của chế độ PIPELINE_MODE=REPLAY (smoke test, demo). Mỗi dòng được đóng gói
bằng `ingestion.envelope.encode_event`: thêm `ingested_at` và `collector_version`, giữ nguyên ID
và timestamp gốc, nên chạy lại cùng file sẽ gửi cùng chuỗi event, cùng key, cùng thứ tự (chỉ
`ingested_at` khác).

Các phần chính:
- `replay_delay`: đổi `--interval` và `--speed` thành thời gian nghỉ giữa hai lần gửi.
- `run_replay`: vòng lặp gửi thuần (không cần Kafka, dễ test); trả về `ReplayStats`, gặp lỗi
  thì báo `ReplaySendError`.
- `main`: CLI. Kiểm tham số, tạo KafkaProducer (`acks=all`), gửi đồng bộ từng event, rồi map lỗi
  sang exit code 0/1/2/3 (các hằng `EXIT_*`). Lỗi khi `close()` chỉ ghi log, không che exit code.
Cách chạy, flags và ý nghĩa từng exit code: xem `replay/README.md`.
"""

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

# Mã 2 trùng với mã argparse dùng khi gọi sai tham số.
EXIT_OK, EXIT_SEND_FAILED, EXIT_USAGE, EXIT_BROKER_UNAVAILABLE = 0, 1, 2, 3

logger = logging.getLogger(__name__)


@dataclass
class ReplayStats:
    """Tiến độ của một lần replay.

    `sent`: số event đã gửi thành công; `skipped_blank`: số dòng trống bị bỏ qua trong khoảng đã
    chọn; `last_index`: chỉ số (từ 0) của dòng cuối cùng gửi thành công, `None` nếu chưa gửi được.
    """

    sent: int = 0
    skipped_blank: int = 0
    last_index: int | None = None


class ReplaySendError(RuntimeError):
    """Báo lần gửi đầu tiên bị lỗi: `index` là chỉ số dòng lỗi, `stats` là tiến độ trước đó.

    Lỗi gốc của producer nằm ở `__cause__`. Chạy lại với `--start <index>` để tiếp tục; các dòng
    gửi sát trước lỗi có thể bị gửi trùng (at-least-once, xem `replay/README.md`).
    """

    def __init__(self, index: int, stats: ReplayStats):
        """Lưu `index` (chỉ số dòng lỗi, từ 0) và `stats` (tiến độ trước dòng đó)."""
        super().__init__(f"send failed at record index {index} after {stats.sent} sent")
        self.index = index
        self.stats = stats


def replay_delay(interval: float, speed: float) -> float:
    """Tính thời gian nghỉ sau mỗi lần gửi: `interval / speed` (giây).

    Báo `ValueError` nếu speed không hữu hạn hoặc <= 0, hay interval không hữu hạn hoặc âm.
    """
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("REPLAY_SPEED_FACTOR must be finite and positive")
    if not math.isfinite(interval) or interval < 0:
        raise ValueError("interval must be finite and non-negative")
    return interval / speed


def _utc_now() -> datetime:
    """Giờ UTC hiện tại; là giá trị mặc định của tham số `now` trong `run_replay`.

    Test truyền hàm giờ cố định vào `now` thay cho hàm này.
    """
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
    """Gửi các dòng có chỉ số trong `[start, end)` theo thứ tự; dừng ở lần gửi lỗi đầu tiên.

    Mỗi dòng được đóng gói bằng `encode_event` rồi đưa cho `send(key, value)`. Dòng trống bị bỏ
    qua nhưng vẫn được tính chỉ số. Sau mỗi lần gửi (kể cả lần cuối) nghỉ `delay` giây; speed
    chỉ ảnh hưởng nhịp gửi, không đổi nội dung hay thứ tự. `send` lỗi thì báo `ReplaySendError`.
    `now` và `sleep` có thể thay khi test.
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
        except Exception as exc:  # mọi lỗi producer đều dừng lần chạy; bên gọi tự map exit code
            raise ReplaySendError(index, stats) from exc
        stats.sent += 1
        stats.last_index = index
        logger.info("event_published index=%s", index)
        if delay:
            sleep(delay)
    return stats


def main() -> None:
    """CLI replay: kiểm tham số, gửi file vào raw topic, rồi thoát với mã `EXIT_*` tương ứng.

    Các lỗi dùng sai được kiểm trước khi kết nối Kafka. Ý nghĩa từng exit code: `replay/README.md`.
    """
    # description giữ tiếng Anh (ASCII), không dùng __doc__ tiếng Việt: `--help` in ra stdout,
    # qua pipe cp1252 trên Windows sẽ báo UnicodeEncodeError.
    parser = argparse.ArgumentParser(
        description="Publish fixture JSONL records without rewriting source timestamps "
                    "or identifiers."
    )
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
        # utf-8-sig bỏ BOM UTF-8 (vd. `Out-File -Encoding utf8` của PowerShell 5.1); đọc bằng
        # utf-8 thường thì dòng 0 thành JSON hỏng và bị gửi vào bronze/invalid.
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
            # Broker chết thì còn batch treo: chỉ chờ close() 5 giây và không để lỗi close()
            # che mất exit code.
            producer.close(timeout=5 if failed else 30)
        except Exception:
            logger.warning("producer_close_failed", exc_info=True)
    logger.info("replay_complete events_published=%s mode=REPLAY topic=%s", stats.sent, topic)


if __name__ == "__main__":
    main()
