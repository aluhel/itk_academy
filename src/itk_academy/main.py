from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from itk_academy.api.middleware import RequestIDMiddleware
from itk_academy.api.v1.router import api_router
from itk_academy.config import get_settings
from itk_academy.core.logging import configure_logging
from itk_academy.db.session import get_engine
from itk_academy.events_provider.client import EventsProviderClient

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("app_starting", app=settings.app, env=settings.env)

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            traces_sample_rate=0.1,
        )
        logger.info("sentry_initialized")

    engine = None
    if settings.database_url:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("db_connection_ok")
        except Exception as exc:
            logger.error("db_connection_failed", error=str(exc))
    else:
        logger.warning("database_url_not_set")

    provider_client = EventsProviderClient(
        base_url=settings.events_provider_url,
        api_key=settings.events_provider_api_key,
    )
    app.state.events_provider_client = provider_client
    logger.info("provider_client_initialized")

    yield

    await provider_client.aclose()
    if engine is not None:
        await engine.dispose()
    logger.info("app_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ITK Academy — Events Aggregator",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Root endpoint for platform health checks."""
        return {"status": "ok"}

    @app.get("/health", include_in_schema=False)
    async def health_root() -> dict[str, str]:
        """Health endpoint for k8s readiness/liveness probes."""
        return {"status": "ok"}

    @app.get("/custom/path", include_in_schema=False)
    async def custom_path() -> PlainTextResponse:
        """Platform smoke-test endpoint. Kept to satisfy the template autotest."""
        return PlainTextResponse("Hello from LMS!\nPath: /custom/path\n")

    app.add_middleware(RequestIDMiddleware)
    app.include_router(api_router, prefix="/api")

    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/docs", "/redoc", "/openapi.json"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
