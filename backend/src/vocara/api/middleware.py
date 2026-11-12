"""HTTP Middlewares for correlation ID, execution timing, structured request logging, and rate limiting."""

import time
import uuid
from collections import defaultdict
from typing import Any
from urllib.parse import parse_qsl, urlencode

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from vocara.core.logging import get_logger, request_id_ctx, tenant_id_ctx, user_id_ctx

logger = get_logger("vocara.http")

SENSITIVE_PARAM_KEYS = {
    "key",
    "api_key",
    "token",
    "secret",
    "password",
    "auth",
    "access_token",
    "authorization",
}


def sanitize_url(path: str, query_string: str) -> str:
    """Sanitize URL to strip sensitive tokens and passwords from query strings."""
    if not query_string:
        return path

    try:
        parsed = parse_qsl(query_string, keep_blank_values=True)
        sanitized: list[tuple[str, str]] = []
        for k, v in parsed:
            if k.lower() in SENSITIVE_PARAM_KEYS:
                sanitized.append((k, "[REDACTED]"))
            else:
                sanitized.append((k, v))
        clean_query = urlencode(sanitized)
        return f"{path}?{clean_query}" if clean_query else path
    except Exception:
        return path


def get_client_ip(request: Request) -> str:
    """Extract client IP respecting X-Forwarded-For and X-Real-IP reverse proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured HTTP Request Logging Middleware implementing engineering standards:
    1. Essential Metadata: timestamp (ISO-8601), requestId, userId, tenantId
    2. Request Details: method, path, url (sanitized), userAgent, ip
    3. Response Details: status, durationMs, responseSize
    4. Performance & Sub-metrics: dbTimeMs, inferenceTimeMs
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind context variables for downstream logging
        token_req = request_id_ctx.set(req_id)
        token_user = user_id_ctx.set(None)
        token_tenant = tenant_id_ctx.set(None)

        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        sanitized_url = sanitize_url(request.url.path, request.url.query)

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            user_id = user_id_ctx.get() or getattr(request.state, "user_id", None) or "anonymous"
            tenant_id = tenant_id_ctx.get() or getattr(request.state, "tenant_id", None) or "default"

            logger.error(
                "http_request_unhandled_exception",
                requestId=req_id,
                userId=user_id,
                tenantId=tenant_id,
                method=request.method,
                path=request.url.path,
                url=sanitized_url,
                userAgent=user_agent,
                ip=client_ip,
                status=500,
                durationMs=duration_ms,
                error=str(exc),
            )
            request_id_ctx.reset(token_req)
            user_id_ctx.reset(token_user)
            tenant_id_ctx.reset(token_tenant)
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        # Content length / response payload size
        content_length = response.headers.get("content-length")
        response_size = (
            int(content_length) if content_length and content_length.isdigit() else None
        )

        user_id = user_id_ctx.get() or getattr(request.state, "user_id", None) or "anonymous"
        tenant_id = tenant_id_ctx.get() or getattr(request.state, "tenant_id", None) or "default"

        log_data: dict[str, Any] = {
            "requestId": req_id,
            "userId": user_id,
            "tenantId": tenant_id,
            "method": request.method,
            "path": request.url.path,
            "url": sanitized_url,
            "userAgent": user_agent,
            "ip": client_ip,
            "status": response.status_code,
            "durationMs": duration_ms,
        }
        if response_size is not None:
            log_data["responseSize"] = response_size

        db_time_ms = getattr(request.state, "db_time_ms", None)
        if db_time_ms is not None:
            log_data["dbTimeMs"] = db_time_ms

        inference_time_ms = getattr(request.state, "inference_time_ms", None)
        if inference_time_ms is not None:
            log_data["inferenceTimeMs"] = inference_time_ms

        if response.status_code >= 500:
            logger.error("http_request_failed", **log_data)
        elif response.status_code >= 400:
            logger.warning("http_request_client_error", **log_data)
        else:
            if request.url.path == "/health":
                logger.debug("http_health_check", **log_data)
            else:
                logger.info("http_request_completed", **log_data)

        request_id_ctx.reset(token_req)
        user_id_ctx.reset(token_user)
        tenant_id_ctx.reset(token_tenant)
        return response


# Backwards compatibility aliases
CorrelationIdMiddleware = RequestLoggingMiddleware
ProcessTimingMiddleware = RequestLoggingMiddleware


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-memory rate limiter per client IP / API key prefix."""

    def __init__(self, app: ASGIApp, default_limit: int = 60) -> None:
        super().__init__(app)
        self.default_limit = default_limit
        # Map: client_id -> list of timestamps
        self.request_records: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Extract API key prefix, session token prefix, or client host as identifier."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer voc_"):
            return auth[7:23]  # API key prefix
        if auth.startswith("Bearer ") and len(auth) > 23:
            return f"jwt_{auth[-16:]}"  # Per-session bucket

        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header.startswith("voc_"):
            return api_key_header[:16]

        client_host = request.client.host if request.client else "unknown"
        return f"ip_{client_host}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exempt health check, docs, and CORS preflight from rate limits
        if request.method == "OPTIONS" or request.url.path in (
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ):
            return await call_next(request)

        # Allow higher burst for read-only GET/HEAD dashboard/metadata requests
        is_read_only = request.method in ("GET", "HEAD")
        effective_limit = self.default_limit * 5 if is_read_only else self.default_limit
        bucket_key = f"{'read' if is_read_only else 'write'}:{self._get_client_id(request)}"

        now = time.time()
        window_start = now - 60.0

        timestamps = self.request_records[bucket_key]
        # Filter timestamps within the 60-second window
        active_timestamps = [t for t in timestamps if t > window_start]
        self.request_records[bucket_key] = active_timestamps

        if len(active_timestamps) >= effective_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit of {effective_limit} requests/minute exceeded. Please wait a moment.",
                    }
                },
            )

        active_timestamps.append(now)
        return await call_next(request)
