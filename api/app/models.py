"""Public schemas distinguish ready CP0 data from owned future work."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from wikipulse_core.serving import ActivityRow


class ActivityEnvelope(BaseModel):
    data: list[ActivityRow]
    generated_at: datetime
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    provisional: Literal[True] = True


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    source: Literal["cassandra"] = "cassandra"
    pipeline_mode: Literal["REPLAY", "LIVE"]
    implementation_status: Literal["activity_only"] = "activity_only"
    dependencies: dict[str, Literal["ready", "unavailable"]]


class DependencyErrorDetail(BaseModel):
    code: Literal["DEPENDENCY_UNAVAILABLE"] = "DEPENDENCY_UNAVAILABLE"
    source: Literal["cassandra"] = "cassandra"


class DependencyErrorResponse(BaseModel):
    detail: DependencyErrorDetail


class NotImplementedResponse(BaseModel):
    code: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"
    feature: Literal["trends", "suspicious-edits", "events"]
    role: Literal["Cassandra/sink/API"] = "Cassandra/sink/API"
    owner: Literal["Nhân"] = "Nhân"
    week: Literal[2] = 2
