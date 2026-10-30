"""HTTP Middlewares for correlation ID, execution timing, and rate limiting."""

import time
import uuid
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from vocara.core.logging import request_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique request correlation ID to context and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


class ProcessTimingMiddleware(BaseHTTPMiddleware):
    """Middleware recording request duration and returning X-Process-Time header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time"] = f"{process_time_ms}ms"
        return response


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-memory rate limiter per client IP / API key prefix."""

    def __init__(self, app: ASGIApp, default_limit: int = 60) -> None:
        super().__init__(app)
        self.default_limit = default_limit
        # Map: client_id -> list of timestamps
        self.request_records: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Extract API key prefix or client host as identifier."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer voc_"):
            return auth[7:23]  # Prefix

        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header.startswith("voc_"):
            return api_key_header[:16]

        client_host = request.client.host if request.client else "unknown"
        return f"ip_{client_host}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exempt health check and docs from rate limits
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        now = time.time()
        window_start = now - 60.0

        timestamps = self.request_records[client_id]
        # Filter timestamps within the 60-second window
        active_timestamps = [t for t in timestamps if t > window_start]
        self.request_records[client_id] = active_timestamps

        if len(active_timestamps) >= self.default_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit of {self.default_limit} requests/minute exceeded.",
                    }
                },
            )

        active_timestamps.append(now)
        return await call_next(request)
