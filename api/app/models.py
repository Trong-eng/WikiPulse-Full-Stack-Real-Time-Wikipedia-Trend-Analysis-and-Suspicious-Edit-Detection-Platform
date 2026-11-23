"""Public schemas of the serving contract (docs/contracts.md, v0.1 activity + v0.2)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from wikipulse_core.serving import ActivityRow, EventDetailRow, SuspiciousEditRow

DISCLAIMER = "Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."


class ActivityEnvelope(BaseModel):
    data: list[ActivityRow]
    generated_at: datetime
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    provisional: Literal[True] = True


class TrendItem(BaseModel):
    """A trend row as published: the storage-only `updated_at` is left out."""

    wiki: str
    page_key: str
    page_title: str | None
    namespace: int | None
    window_start: datetime
    window_end: datetime
    edit_count: int
    unique_editors: int
    abs_byte_delta: int
    trend_score: float


class TrendEnvelope(BaseModel):
    data: list[TrendItem]
    window_start: datetime | None
    window_end: datetime | None
    generated_at: datetime
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    provisional: Literal[True] = True


class SuspiciousEditEnvelope(BaseModel):
    data: list[SuspiciousEditRow]
    generated_at: datetime
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    provisional: Literal[True] = True
    disclaimer: Literal["Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."] = DISCLAIMER


class EventEnvelope(BaseModel):
    data: EventDetailRow
    generated_at: datetime
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    implementation_status: Literal["activity_trends_suspicious_events"] = (
        "activity_trends_suspicious_events"
    )
    dependencies: dict[str, Literal["ready", "unavailable"]]


class FieldError(BaseModel):
    name: str
    message: str


class ErrorDetail(BaseModel):
    """Every error: `{"detail": {"code", "message", ...}}`; extra fields depend on the code."""

    code: Literal[
        "INVALID_QUERY", "EVENT_NOT_FOUND", "DEPENDENCY_UNAVAILABLE", "CAPACITY_EXCEEDED"
    ]
    message: str
    source: Literal["cassandra"] | None = None
    fields: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetail
