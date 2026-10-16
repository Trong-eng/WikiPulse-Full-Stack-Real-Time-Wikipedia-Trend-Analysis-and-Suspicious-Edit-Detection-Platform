"""Envelope Kafka dùng chung cho replay và collector LIVE (xem docs/contracts.md, mục Kafka).

File này quyết định một event Wikipedia trông như thế nào khi được ghi vào raw topic:
- `collector_version(source)`: phiên bản gắn vào payload, để Spark biết event đến từ replay
  hay LIVE.
- `message_key(event)`: key Kafka `wiki:page_id` (có fallback). Cùng key luôn vào cùng partition,
  nên event của một trang trong cùng một nguồn giữ được thứ tự.
- `encode_event(line, now, source=...)`: đóng gói một dòng JSON thành `(key, payload)`, kể cả
  dòng hỏng và dòng có surrogate lẻ.
Quy tắc chi tiết nằm ở docstring từng hàm. Contract: `docs/contracts.md` (mục Kafka) và
`replay/README.md` (mục Envelope).
"""

import json
import os
from datetime import datetime


def collector_version(source: str) -> str:
    """Trả về chuỗi `<source>-<COLLECTOR_VERSION>`, ví dụ `replay-0.1.0` hoặc `live-0.1.0`.

    Biến môi trường `COLLECTOR_VERSION` không được đặt thì dùng `0.1.0`.
    """
    return f"{source}-{os.getenv('COLLECTOR_VERSION', '0.1.0')}"


def message_key(event: dict) -> bytes:
    """Tạo key Kafka (bytes UTF-8) cho một event đã parse.

    Dạng `wiki:page_id`; page_id thiếu hoặc null thì dùng `wiki:title`. wiki hoặc title thiếu,
    null hay rỗng thì thay bằng `unknown`; page_id bằng 0 vẫn được giữ.
    """
    wiki = event.get("wiki") or "unknown"
    page = event.get("page_id")
    if page is None:
        page = event.get("title") or "unknown"
    # backslashreplace: title chứa surrogate lẻ không được làm crash bước tạo key.
    return f"{wiki}:{page}".encode("utf-8", "backslashreplace")


def encode_event(line: str, now: datetime, *, source: str = "replay") -> tuple[bytes | None, bytes]:
    """Đóng gói một dòng JSON thành `(key, payload)` để gửi vào Kafka.

    Thêm `ingested_at` (giờ `now`, dạng ISO) và `collector_version(source)`; không đụng tới ID hay
    timestamp gốc của nguồn. Dòng JSON hỏng hoặc không phải object thì trả về `(None, line)`
    nguyên văn để Spark đưa vào bronze/invalid. Nếu escape surrogate lẻ làm event không mã hoá
    được UTF-8, toàn bộ payload được dump ở dạng ASCII-escape.
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
