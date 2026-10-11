"""FastAPI application; only Cassandra-backed activity is implemented in CP0."""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging
from wikipulse_core.serving import CassandraActivityStore

from api.app.models import ActivityEnvelope, HealthResponse, NotImplementedResponse

logger = logging.getLogger(__name__)


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

    application = FastAPI(title="WikiPulse API", version="0.1.0", lifespan=lifespan)

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

    @application.get("/api/v1/activity", response_model=ActivityEnvelope)
    def activity(
        request: Request,
        wiki: Annotated[
            str, Query(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
        ] = "enwiki",
        window: datetime | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> ActivityEnvelope:
        if wiki not in settings.wiki_allowlist:
            raise HTTPException(status_code=422, detail="wiki must be in WIKI_ALLOWLIST")
        if window is not None and (window.tzinfo is None or window.utcoffset() is None):
            raise HTTPException(status_code=422, detail="window must include a UTC timezone")
        if window is not None:
            window = window.astimezone(timezone.utc)
        try:
            rows = request.app.state.activity_store.get_activity(wiki, window=window, limit=limit)
        except Exception as exc:
            logger.warning("Cassandra activity query failed")
            raise HTTPException(
                status_code=503, detail={"code": "DEPENDENCY_UNAVAILABLE", "source": "cassandra"}
            ) from exc
        return ActivityEnvelope(
            data=rows, generated_at=datetime.now(timezone.utc), pipeline_mode=settings.pipeline_mode
        )

    @application.get("/api/v1/trends", response_model=NotImplementedResponse, status_code=501)
    def trends() -> NotImplementedResponse:
        return NotImplementedResponse(feature="trends")

    @application.get(
        "/api/v1/suspicious-edits", response_model=NotImplementedResponse, status_code=501
    )
    def suspicious_edits() -> NotImplementedResponse:
        return NotImplementedResponse(feature="suspicious-edits")

    @application.get(
        "/api/v1/events/{event_id}", response_model=NotImplementedResponse, status_code=501
    )
    def event(event_id: str) -> NotImplementedResponse:
        return NotImplementedResponse(feature="events")

    return application


app = create_app()
