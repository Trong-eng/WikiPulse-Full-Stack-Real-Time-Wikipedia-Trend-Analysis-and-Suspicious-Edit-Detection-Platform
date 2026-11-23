"""Phân tích sự kiện SSE mà không lưu payload hoặc diễn giải ID nguồn."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class SSEEvent:
    data: str
    id: str | None


def parse_sse(lines: Iterable[str], *, initial_id: str | None = None) -> Iterator[SSEEvent]:
    """Nhận dòng đã bỏ delimiter, chỉ phát event hoàn chỉnh kết thúc bằng dòng trống."""
    event_id = initial_id
    data = []
    for index, line in enumerate(lines):
        if index == 0:
            line = line.removeprefix("\ufeff")
        if not line:
            if data:
                yield SSEEvent("\n".join(data), event_id)
            data = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "data":
            data.append(value)
        elif field == "id" and "\x00" not in value:
            event_id = value
