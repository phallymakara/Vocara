"""HTTP error handlers mapping domain exceptions to standard JSON responses."""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from vocara.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConsentRequiredError,
    EntityNotFoundError,
    InvalidAudioError,
    InvalidWebhookUrlError,
    QuotaExceededError,
    RateLimitExceededError,
    VocaraError,
)

logger = structlog.get_logger("vocara.error_handlers")


def register_error_handlers(app: FastAPI) -> None:
    """Attach standard exception handlers to the FastAPI application."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_not_found(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(AuthenticationError)
    async def handle_unauthorized(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(AuthorizationError)
    async def handle_forbidden(_: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(QuotaExceededError)
    async def handle_quota_exceeded(_: Request, exc: QuotaExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RateLimitExceededError)
    async def handle_rate_limit(_: Request, exc: RateLimitExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ConsentRequiredError)
    async def handle_consent_required(_: Request, exc: ConsentRequiredError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(InvalidWebhookUrlError)
    async def handle_invalid_webhook_url(_: Request, exc: InvalidWebhookUrlError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(InvalidAudioError)
    async def handle_invalid_audio(_: Request, exc: InvalidAudioError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(VocaraError)
    async def handle_generic_domain_error(_: Request, exc: VocaraError) -> JSONResponse:
        logger.error("domain_error", code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_system_exception", error=str(exc))
        # Keep internal details safe and hidden from clients
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                }
            },
        )
