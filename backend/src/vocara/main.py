"""FastAPI Application Entrypoint and Lifespan Manager."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from vocara.api.middleware import (
    InMemoryRateLimiterMiddleware,
    RequestLoggingMiddleware,
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
    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        host=settings.HOST,
        port=settings.PORT,
        projectName=settings.PROJECT_NAME,
        inferenceEngine=settings.INFERENCE_ENGINE_TYPE,
        storageBackend=settings.STORAGE_BACKEND,
    )

    container: Container = app.state.container
    await container.initialize()
    logger.info(
        "application_ready",
        host=settings.HOST,
        port=settings.PORT,
        docsUrl=f"http://{settings.HOST}:{settings.PORT}/docs" if settings.DEBUG else None,
        mcpUrl=f"http://{settings.HOST}:{settings.PORT}/mcp/sse",
    )

    try:
        yield
    finally:
        logger.info("application_shutdown")
        await container.shutdown()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for Vocara Voice API."""
    cfg = settings or get_settings()

    docs_enabled = cfg.DEBUG or cfg.ENVIRONMENT != "production"
    app = FastAPI(
        title=cfg.PROJECT_NAME,
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        lifespan=lifespan,
    )

    # State injection
    app.state.settings = cfg
    app.state.container = Container(cfg)

    # Middlewares (executed in reverse order of addition: Logging -> Limiter -> CORS)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        InMemoryRateLimiterMiddleware,
        default_limit=cfg.DEFAULT_RATE_LIMIT_PER_MINUTE,
    )
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

    # Mount Model Context Protocol (MCP) Server for external developers & AI agents
    from vocara.mcp.transport_sse import get_mcp_asgi_app

    mcp_app = get_mcp_asgi_app(app.state.container)
    app.mount("/mcp", mcp_app)

    # Root & Baseline Health Check
    @app.get("/", include_in_schema=False, response_model=None)
    async def root() -> Response:
        if docs_enabled:
            return RedirectResponse(url="/docs")
        return Response(content='{"status":"healthy"}', media_type="application/json")

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
    from pathlib import Path
    import uvicorn

    cfg = get_settings()
    setup_logging(log_level=cfg.LOG_LEVEL, log_format=cfg.LOG_FORMAT)
    src_dir = str(Path(__file__).parent.resolve())
    uvicorn.run(
        "vocara.main:app",
        host=cfg.HOST,
        port=cfg.PORT,
        reload=cfg.DEBUG,
        reload_dirs=[src_dir] if cfg.DEBUG else None,
        reload_excludes=[
            "storage_local",
            "*.wav",
            "*.mp3",
            "*.ogg",
            "*.flac",
            "*.db",
            "*.db-wal",
            "*.db-shm",
        ]
        if cfg.DEBUG
        else None,
        workers=cfg.WORKERS if not cfg.DEBUG else 1,
        access_log=False,
    )


if __name__ == "__main__":
    run()
