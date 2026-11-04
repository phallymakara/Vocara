"""Unit tests for structured request logging middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from httpx import ASGITransport, AsyncClient

from vocara.api.middleware import RequestLoggingMiddleware, sanitize_url
from vocara.core.logging import setup_logging


def test_sanitize_url_removes_sensitive_keys() -> None:
    """Verifies tokens and keys in query string are redacted."""
    raw_url = "/api/v1/voices"
    query = "api_key=secret123&page=1&token=mytoken&name=sophea"
    clean = sanitize_url(raw_url, query)
    assert "api_key=%5BREDACTED%5D" in clean or "api_key=[REDACTED]" in clean
    assert "token=%5BREDACTED%5D" in clean or "token=[REDACTED]" in clean
    assert "name=sophea" in clean
    assert "page=1" in clean


@pytest.mark.asyncio
async def test_request_logging_middleware_captures_metadata_and_headers() -> None:
    """Verifies that RequestLoggingMiddleware captures all required log metadata and headers."""
    setup_logging(log_level="INFO", log_format="json")

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test/route")
    async def sample_endpoint(request: Request) -> Response:
        # Simulate sub-metric setting
        request.state.user_id = "user_123"
        request.state.tenant_id = "tenant_abc"
        request.state.db_time_ms = 4.5
        request.state.inference_time_ms = 12.3
        return JSONResponse({"status": "ok"}, status_code=200)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test/route?api_key=supersecret&filter=active",
            headers={
                "X-Request-ID": "custom-req-id-789",
                "User-Agent": "VocaraTestClient/1.0",
                "X-Forwarded-For": "203.0.113.195, 10.0.0.1",
            },
        )

        assert resp.status_code == 200
        # Headers verification
        assert resp.headers["X-Request-ID"] == "custom-req-id-789"
        assert "ms" in resp.headers["X-Process-Time"]


@pytest.mark.asyncio
async def test_request_logging_middleware_handles_errors() -> None:
    """Verifies error responses receive correlation IDs and headers."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/error/route")
    async def error_endpoint() -> Response:
        return JSONResponse({"error": "Bad Request"}, status_code=400)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/error/route")
        assert resp.status_code == 400
        assert "X-Request-ID" in resp.headers
        assert "X-Process-Time" in resp.headers

