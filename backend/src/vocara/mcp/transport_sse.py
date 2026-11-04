"""FastAPI / Starlette SSE Transport integration for Vocara MCP Server."""

from typing import Any

from starlette.datastructures import Headers, QueryParams
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from vocara.container import Container
from vocara.core.exceptions import AuthenticationError
from vocara.core.logging import get_logger, tenant_id_ctx, user_id_ctx
from vocara.mcp.server import create_mcp_server, current_mcp_key_ctx

logger = get_logger("vocara.mcp.transport")


class McpAuthMiddleware:
    """Pure ASGI middleware to authenticate external developers connecting to the MCP Server."""

    def __init__(self, app: ASGIApp, container: Container) -> None:
        self.app = app
        self.container = container

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        query = QueryParams(scope.get("query_string", b"").decode("latin1"))

        raw_key: str | None = None
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_key = auth_header[7:].strip()
        elif headers.get("x-api-key"):
            raw_key = headers.get("x-api-key", "").strip()
        elif "api_key" in query:
            raw_key = query["api_key"].strip()

        if not self.container.session_factory:
            response = JSONResponse(
                status_code=500,
                content={"error": "Database session factory not initialized"},
            )
            await response(scope, receive, send)
            return

        async with self.container.session_factory() as session:
            auth_service = self.container.get_auth_service(session)
            api_key = None

            if raw_key:
                try:
                    api_key = await auth_service.authenticate_key(raw_key)
                except AuthenticationError:
                    response = JSONResponse(
                        status_code=401,
                        content={
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Invalid or inactive Vocara API key provided.",
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return

            # Auto-fallback to development workspace key in local development when no key is passed
            if api_key is None:
                if self.container.settings.ENVIRONMENT == "development":
                    api_key = await auth_service.get_or_create_dev_key()
                else:
                    response = JSONResponse(
                        status_code=401,
                        content={
                            "error": {
                                "code": "AUTHENTICATION_REQUIRED",
                                "message": (
                                    "Vocara API key required. Provide via 'X-API-Key' header, "
                                    "'Authorization: Bearer <key>', or '?api_key=<key>' query parameter."
                                ),
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return

            # Bind tenant context for MCP tool execution
            token_key = current_mcp_key_ctx.set(api_key)
            token_user = user_id_ctx.set(api_key.owner_id)
            token_tenant = tenant_id_ctx.set(api_key.owner_id)

            try:
                await self.app(scope, receive, send)
            finally:
                current_mcp_key_ctx.reset(token_key)
                user_id_ctx.reset(token_user)
                tenant_id_ctx.reset(token_tenant)


def get_mcp_asgi_app(container: Container) -> Any:
    """Create Starlette ASGI app for MCP SSE with authentication middleware."""
    from mcp.server.sse import TransportSecuritySettings

    mcp_server = create_mcp_server(container)
    transport_sec = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,  # Allow external developer proxies, domains & test harnesses
    )
    sse_app = mcp_server.sse_app(transport_security=transport_sec)
    return McpAuthMiddleware(sse_app, container=container)
