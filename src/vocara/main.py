"""FastAPI Application Entrypoint and Lifespan Manager."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vocara.api.middleware import (
    CorrelationIdMiddleware,
    InMemoryRateLimiterMiddleware,
    ProcessTimingMiddleware,
)
from vocara.api.v1.router import api_v1_router
from vocara.container import Container
from vocara.core.config import Settings, get_settings
from vocara.core.error_handlers import register_error_handlers
from vocara.core.logging import get_logger, setup_logging

logger = get_logger("vocara.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager handling startup and shutdown hooks."""
    settings: Settings = app.state.settings
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info("application_startup", environment=settings.ENVIRONMENT)

    container: Container = app.state.container
    await container.initialize()

    try:
        yield
    finally:
        logger.info("application_shutdown")
        await container.shutdown()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for Vocara Voice API."""
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.PROJECT_NAME,
        version="0.1.0",
        docs_url="/docs" if cfg.DEBUG else None,
        redoc_url="/redoc" if cfg.DEBUG else None,
        lifespan=lifespan,
    )

    # State injection
    app.state.settings = cfg
    app.state.container = Container(cfg)

    # Middlewares (executed in reverse order of addition: Timing -> Limiter -> Correlation -> CORS)
    app.add_middleware(ProcessTimingMiddleware)
    app.add_middleware(
        InMemoryRateLimiterMiddleware,
        default_limit=cfg.DEFAULT_RATE_LIMIT_PER_MINUTE,
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if cfg.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Centralized Error Handlers
    register_error_handlers(app)

    # Mount API v1 Routes
    app.include_router(api_v1_router, prefix=cfg.API_V1_PREFIX)

    # Baseline Health Check
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "vocara-api",
            "environment": cfg.ENVIRONMENT,
        }

    return app


# Default app instance
app = create_app()


def run() -> None:
    """CLI entrypoint executed via 'uv run vocara'."""
    import uvicorn

    cfg = get_settings()
    uvicorn.run(
        "vocara.main:app",
        host=cfg.HOST,
        port=cfg.PORT,
        reload=cfg.DEBUG,
        workers=cfg.WORKERS if not cfg.DEBUG else 1,
    )


if __name__ == "__main__":
    run()
