"""FastAPI application serving Cassandra-backed activity, trends, suspicious edits and events."""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging
from wikipulse_core.serving import (
    MAX_SUSPICIOUS_MINUTES,
    TREND_WINDOW,
    CapacityExceeded,
    CassandraActivityStore,
)

from api.app.models import (
    ActivityEnvelope,
    ErrorResponse,
    EventEnvelope,
    HealthResponse,
    SuspiciousEditEnvelope,
    TrendEnvelope,
)

logger = logging.getLogger(__name__)

WikiParam = Annotated[str, Query(
    min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$",
    description="Wiki in WIKI_ALLOWLIST, e.g. enwiki.",
)]
LimitParam = Annotated[int, Query(ge=1, le=100, description="Maximum rows returned.")]
WindowParam = Annotated[datetime | None, Query(
    description="Timezone-aware ISO window start; omitted means the latest window.",
)]
QUERY_ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def api_error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


def invalid_query(name: str, message: str) -> HTTPException:
    return api_error(422, "INVALID_QUERY", message, fields=[{"name": name, "message": message}])


def create_app(
    settings: Settings | None = None,
    store_factory: Callable[[Settings], CassandraActivityStore] = CassandraActivityStore,
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configure_logging("api")
        store = store_factory(settings)
        application.state.activity_store = store
        try:
            try:
                store.health()
            except Exception:
                # Start unready so an outage is observable through HTTP 503 and can recover.
                logger.warning("Cassandra is unavailable during API startup")
            yield
        finally:
            store.close()

    application = FastAPI(title="WikiPulse API", version="0.2.0", lifespan=lifespan)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Same shape as every other error instead of FastAPI's default list.
        fields = [
            {"name": str(error["loc"][-1]), "message": error["msg"]} for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": {
            "code": "INVALID_QUERY", "message": "Invalid query parameters", "fields": fields,
        }})

    def checked(wiki: str, window: datetime | None) -> datetime | None:
        if wiki not in settings.wiki_allowlist:
            raise invalid_query("wiki", "wiki must be in WIKI_ALLOWLIST")
        if window is not None and (window.tzinfo is None or window.utcoffset() is None):
            raise invalid_query("window", "window must include a UTC timezone")
        return window.astimezone(timezone.utc) if window is not None else None

    def query(request: Request, method: str, *args, **kwargs):
        try:
            return getattr(request.app.state.activity_store, method)(*args, **kwargs)
        except CapacityExceeded as exc:
            raise api_error(503, "CAPACITY_EXCEEDED", str(exc)) from exc
        except Exception as exc:
            logger.warning("Cassandra query failed: %s", method)
            raise api_error(
                503, "DEPENDENCY_UNAVAILABLE", "Cassandra is unavailable", source="cassandra"
            ) from exc

    def now() -> datetime:
        return datetime.now(timezone.utc)

    @application.get(
        "/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}}
    )
    def health(request: Request, response: Response) -> HealthResponse:
        try:
            ready = request.app.state.activity_store.health()
        except Exception:
            ready = False
        if not ready:
            response.status_code = 503
        return HealthResponse(
            status="ok" if ready else "unavailable",
            pipeline_mode=settings.pipeline_mode,
            dependencies={"cassandra": "ready" if ready else "unavailable"},
        )

    @application.get("/api/v1/activity", response_model=ActivityEnvelope, responses=QUERY_ERRORS)
    def activity(
        request: Request,
        wiki: WikiParam = "enwiki",
        window: WindowParam = None,
        limit: LimitParam = 20,
    ) -> ActivityEnvelope:
        """One-minute activity windows of a wiki, newest first; one window when `window` is set."""
        window = checked(wiki, window)
        rows = query(request, "get_activity", wiki, window=window, limit=limit)
        return ActivityEnvelope(data=rows, generated_at=now(), pipeline_mode=settings.pipeline_mode)

    @application.get("/api/v1/trends", response_model=TrendEnvelope, responses=QUERY_ERRORS)
    def trends(
        request: Request,
        wiki: WikiParam = "enwiki",
        window: WindowParam = None,
        limit: LimitParam = 20,
    ) -> TrendEnvelope:
        """Top pages of one 5-minute window; the latest window when `window` is omitted."""
        window = checked(wiki, window)
        start, rows = query(request, "get_trends", wiki, window=window, limit=limit)
        return TrendEnvelope(
            data=rows,
            window_start=start,
            window_end=start + TREND_WINDOW if start else None,
            generated_at=now(),
            pipeline_mode=settings.pipeline_mode,
        )

    @application.get(
        "/api/v1/suspicious-edits", response_model=SuspiciousEditEnvelope, responses=QUERY_ERRORS
    )
    def suspicious_edits(
        request: Request,
        wiki: WikiParam = "enwiki",
        window: WindowParam = None,
        minutes: Annotated[int, Query(
            ge=1, le=MAX_SUSPICIOUS_MINUTES, description="One-minute buckets to read."
        )] = 5,
        min_score: Annotated[int, Query(
            ge=0, le=100, description="Lowest risk_score returned."
        )] = 0,
        limit: LimitParam = 20,
    ) -> SuspiciousEditEnvelope:
        """Edits of the last `minutes` one-minute buckets ending at `window` or the latest one."""
        window = checked(wiki, window)
        rows = query(
            request, "get_suspicious_edits", wiki,
            window=window, minutes=minutes, min_score=min_score, limit=limit,
        )
        return SuspiciousEditEnvelope(
            data=rows, generated_at=now(), pipeline_mode=settings.pipeline_mode
        )

    @application.get(
        "/api/v1/events/{event_id}",
        response_model=EventEnvelope,
        responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def event(
        request: Request, event_id: Annotated[str, Path(min_length=1, max_length=256)]
    ) -> EventEnvelope:
        """Detail of one Silver event, kept 7 days; 404 EVENT_NOT_FOUND when absent or expired."""
        row = query(request, "get_event", event_id)
        if row is None:
            raise api_error(404, "EVENT_NOT_FOUND", "No event with this event_id")
        return EventEnvelope(data=row, generated_at=now(), pipeline_mode=settings.pipeline_mode)

    return application


app = create_app()
