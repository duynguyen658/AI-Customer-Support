from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from app.api.health import router as health_router
from app.api.tickets import router as tickets_router
from app.core.config import get_settings
from app.core.exceptions import add_exception_handlers
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        app_env=settings.app_env,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


add_exception_handlers(app, logger)
app.include_router(health_router)
app.include_router(tickets_router, prefix=settings.api_v1_prefix)

