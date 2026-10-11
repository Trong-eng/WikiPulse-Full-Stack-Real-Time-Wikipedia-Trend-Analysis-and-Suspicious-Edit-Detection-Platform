"""A small, timeout-bound client for the serving contract.

The client returns explicit states for the UI. It never fills missing activity
with zeros, retries silently, or substitutes fixture data for an API response.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class APIResult:
    state: Literal["ok", "empty", "not_implemented", "unavailable", "error"]
    payload: dict[str, Any] | None = None
    status_code: int | None = None
    message: str = ""


class APIClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _get(self, path: str, params: dict[str, Any] | None = None) -> APIResult:
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self.timeout, transport=self.transport
            ) as client:
                response = client.get(path, params=params)
        except httpx.TimeoutException:
            return APIResult(
                "unavailable", message="API phản hồi quá thời gian. Hãy thử làm mới."
            )
        except httpx.RequestError:
            return APIResult(
                "unavailable", message="Không thể kết nối API. Hãy kiểm tra System Status."
            )

        try:
            payload = response.json()
        except ValueError:
            return APIResult(
                "error",
                status_code=response.status_code,
                message=f"API HTTP {response.status_code} trả về JSON không hợp lệ.",
            )
        if not isinstance(payload, dict):
            return APIResult(
                "error",
                status_code=response.status_code,
                message="API trả về dữ liệu không đúng contract (cần JSON object).",
            )
        if response.status_code == 501:
            return APIResult(
                "not_implemented", payload, 501, "API HTTP 501 · Chưa triển khai."
            )
        if response.status_code >= 500:
            return APIResult(
                "unavailable",
                payload,
                response.status_code,
                f"API HTTP {response.status_code} · Dịch vụ chưa sẵn sàng.",
            )
        if not response.is_success:
            return APIResult(
                "error", payload, response.status_code, f"Yêu cầu lỗi · API HTTP {response.status_code}."
            )
        return APIResult("ok", payload, response.status_code)

    def get_activity(
        self, wiki: str = "enwiki", *, window: str | None = None, limit: int = 20
    ) -> APIResult:
        params: dict[str, Any] = {"wiki": wiki, "limit": limit}
        if window is not None:
            params["window"] = window
        result = self._get("/api/v1/activity", params)
        if result.state != "ok":
            return result
        if not _valid_activity(result.payload, wiki):
            return APIResult(
                "error",
                status_code=result.status_code,
                message="Phản hồi activity không đúng contract; chưa thể hiển thị chỉ số.",
            )
        if not result.payload["data"]:
            return APIResult("empty", result.payload, result.status_code)
        return result

    def get_health(self) -> APIResult:
        return self._get("/health")

    def get_trends(self, wiki: str = "enwiki") -> APIResult:
        return self._get("/api/v1/trends", {"wiki": wiki})

    def get_suspicious_edits(self, wiki: str = "enwiki") -> APIResult:
        return self._get("/api/v1/suspicious-edits", {"wiki": wiki})

    def get_event(self, event_id: str) -> APIResult:
        return self._get(f"/api/v1/events/{quote(event_id, safe='')}")


def _is_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _valid_activity(payload: dict[str, Any], wiki: str) -> bool:
    if (
        not isinstance(payload.get("data"), list)
        or payload.get("source") != "cassandra"
        or payload.get("pipeline_mode") not in ("LIVE", "REPLAY")
        or not isinstance(payload.get("provisional"), bool)
        or not _is_utc(payload.get("generated_at"))
    ):
        return False
    counts = (
        "event_count",
        "edit_count",
        "new_page_count",
        "anonymous_edit_count",
        "bot_edit_count",
    )
    for row in payload["data"]:
        if not isinstance(row, dict) or row.get("wiki") != wiki:
            return False
        if not all(_is_utc(row.get(field)) for field in ("window_start", "window_end", "updated_at")):
            return False
        if not all(type(row.get(field)) is int and row[field] >= 0 for field in counts):
            return False
    return True
