"""A small, timeout-bound client for the serving contract.

The client returns explicit states for the UI. It never fills missing activity
with zeros, retries silently, or substitutes fixture data for an API response.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

import httpx

ALLOWED_RISK_REASONS = ("LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT")
DISCLAIMER_TEXT = "Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."


@dataclass(frozen=True)
class APIResult:
    state: Literal["ok", "empty", "not_implemented", "unavailable", "error"]
    payload: dict[str, Any] | None = None
    status_code: int | None = None
    message: str = ""
    error_code: str | None = None


def _parse_error_detail(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    detail = payload.get("detail")
    if isinstance(detail, dict):
        code = detail.get("code")
        message = detail.get("message")
        return (
            code if isinstance(code, str) else None,
            message if isinstance(message, str) else None,
        )
    return None, None


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

        error_code, error_message = _parse_error_detail(payload)

        if response.status_code == 501:
            return APIResult(
                "not_implemented",
                payload,
                501,
                "API HTTP 501 · Chưa triển khai.",
                error_code=error_code or "NOT_IMPLEMENTED",
            )
        if response.status_code >= 500:
            if error_code == "CAPACITY_EXCEEDED":
                return APIResult(
                    "error",
                    payload,
                    response.status_code,
                    "Dữ liệu cửa sổ vượt quá giới hạn 5.000 dòng, "
                    "vui lòng thu hẹp bộ lọc hoặc chọn cửa sổ khác.",
                    error_code=error_code,
                )
            return APIResult(
                "unavailable",
                payload,
                response.status_code,
                f"API HTTP {response.status_code} · Dịch vụ chưa sẵn sàng.",
                error_code=error_code,
            )
        if not response.is_success:
            if error_code == "EVENT_NOT_FOUND":
                msg = "Không tìm thấy sự kiện với event_id này (có thể đã hết hạn TTL 7 ngày)."
            elif error_code == "INVALID_QUERY" and error_message:
                msg = f"Tham số truy vấn không hợp lệ (HTTP {response.status_code}): {error_message}"
            else:
                msg = f"Yêu cầu lỗi · API HTTP {response.status_code}."
            return APIResult(
                "error",
                payload,
                response.status_code,
                msg,
                error_code=error_code,
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

    def get_trends(
        self, wiki: str = "enwiki", *, window: str | None = None, limit: int = 20
    ) -> APIResult:
        params: dict[str, Any] = {"wiki": wiki, "limit": limit}
        if window is not None:
            params["window"] = window
        result = self._get("/api/v1/trends", params)
        if result.state != "ok":
            return result
        if not _valid_trends(result.payload, wiki):
            return APIResult(
                "error",
                status_code=result.status_code,
                message="Phản hồi trends không đúng contract; chưa thể hiển thị bảng xu hướng.",
            )
        if not result.payload["data"]:
            return APIResult("empty", result.payload, result.status_code)
        return result

    def get_suspicious_edits(
        self,
        wiki: str = "enwiki",
        *,
        window: str | None = None,
        minutes: int = 5,
        min_score: int = 0,
        limit: int = 20,
    ) -> APIResult:
        params: dict[str, Any] = {
            "wiki": wiki,
            "minutes": minutes,
            "min_score": min_score,
            "limit": limit,
        }
        if window is not None:
            params["window"] = window
        result = self._get("/api/v1/suspicious-edits", params)
        if result.state != "ok":
            return result
        if not _valid_suspicious_edits(result.payload, wiki):
            return APIResult(
                "error",
                status_code=result.status_code,
                message="Phản hồi suspicious-edits không đúng contract; chưa thể hiển thị.",
            )
        if not result.payload["data"]:
            return APIResult("empty", result.payload, result.status_code)
        return result

    def get_event(self, event_id: str) -> APIResult:
        result = self._get(f"/api/v1/events/{quote(event_id, safe='')}")
        if result.state != "ok":
            return result
        if not _valid_event_detail(result.payload):
            return APIResult(
                "error",
                status_code=result.status_code,
                message="Phản hồi chi tiết sự kiện không đúng contract.",
            )
        return result


def _is_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _valid_envelope(payload: dict[str, Any], *, require_provisional: bool = True) -> bool:
    if (
        payload.get("source") != "cassandra"
        or payload.get("pipeline_mode") not in ("LIVE", "REPLAY")
        or not _is_utc(payload.get("generated_at"))
    ):
        return False
    if require_provisional and not isinstance(payload.get("provisional"), bool):
        return False
    return True


def _is_non_neg_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _valid_activity(payload: dict[str, Any], wiki: str) -> bool:
    if not isinstance(payload.get("data"), list) or not _valid_envelope(payload):
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
        if not all(_is_non_neg_int(row.get(field)) for field in counts):
            return False
    return True


def _valid_trends(payload: dict[str, Any], wiki: str) -> bool:
    data = payload.get("data")
    if not isinstance(data, list) or not _valid_envelope(payload):
        return False
    window_start = payload.get("window_start")
    window_end = payload.get("window_end")
    if not data:
        if (window_start is None) != (window_end is None):
            return False
        if window_start is not None and not (_is_utc(window_start) and _is_utc(window_end)):
            return False
        return True
    if not (_is_utc(window_start) and _is_utc(window_end)):
        return False

    for row in data:
        if not isinstance(row, dict) or row.get("wiki") != wiki:
            return False
        if not isinstance(row.get("page_key"), str):
            return False
        if row.get("page_title") is not None and not isinstance(row.get("page_title"), str):
            return False
        if row.get("namespace") is not None and type(row.get("namespace")) is not int:
            return False
        if not (_is_utc(row.get("window_start")) and _is_utc(row.get("window_end"))):
            return False
        if not all(
            _is_non_neg_int(row.get(f)) for f in ("edit_count", "unique_editors", "abs_byte_delta")
        ):
            return False
        score = row.get("trend_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 0:
            return False
    return True


def _valid_suspicious_edits(payload: dict[str, Any], wiki: str) -> bool:
    data = payload.get("data")
    if (
        not isinstance(data, list)
        or not _valid_envelope(payload)
        or not isinstance(payload.get("disclaimer"), str)
    ):
        return False
    for row in data:
        if not isinstance(row, dict) or row.get("wiki") != wiki:
            return False
        if "user_hash" in row or "comment" in row:
            return False
        if not isinstance(row.get("event_id"), str) or not isinstance(row.get("page_key"), str):
            return False
        if row.get("page_title") is not None and not isinstance(row.get("page_title"), str):
            return False
        if not all(_is_utc(row.get(f)) for f in ("bucket_start", "event_time", "updated_at")):
            return False
        if not isinstance(row.get("is_anonymous"), bool) or not isinstance(row.get("is_bot"), bool):
            return False
        score = row.get("risk_score")
        if type(score) is not int or not (0 <= score <= 100):
            return False
        reasons = row.get("risk_reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(r, str) and r in ALLOWED_RISK_REASONS for r in reasons
        ):
            return False
    return True


def _valid_event_detail(payload: dict[str, Any]) -> bool:
    data = payload.get("data")
    if not isinstance(data, dict) or not _valid_envelope(payload, require_provisional=False):
        return False
    if "user_hash" in data or "comment" in data:
        return False
    if (
        not isinstance(data.get("event_id"), str)
        or not isinstance(data.get("wiki"), str)
        or not _is_utc(data.get("event_time"))
        or not isinstance(data.get("page_key"), str)
        or not isinstance(data.get("event_type"), str)
    ):
        return False
    if not all(
        isinstance(data.get(f), bool) for f in ("is_anonymous", "is_bot", "is_minor")
    ):
        return False
    score = data.get("risk_score")
    if type(score) is not int or not (0 <= score <= 100):
        return False
    reasons = data.get("risk_reasons")
    if not isinstance(reasons, list) or not all(isinstance(r, str) for r in reasons):
        return False
    return True
