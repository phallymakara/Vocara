"""FastAPI dependency providers for authentication, database sessions, and services."""

import time
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.container import Container
from vocara.core.config import Settings
from vocara.core.exceptions import AuthenticationError
from vocara.core.logging import tenant_id_ctx, user_id_ctx
from vocara.domain.entities import ApiKey
from vocara.services.auth_service import AuthService
from vocara.services.job_service import JobService
from vocara.services.tts_service import TtsService
from vocara.services.usage_service import UsageService
from vocara.services.voice_service import VoiceService
from vocara.services.webhook_service import WebhookService

api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    """Extract DI container from application state."""
    container: Container = request.app.state.container
    return container


async def get_db_session(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide scoped async database session and track execution timing."""
    if not container.session_factory:
        raise RuntimeError("Database session factory is not initialized.")

    t0 = time.perf_counter()
    async with container.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            db_ms = round((time.perf_counter() - t0) * 1000, 2)
            current_db_time = getattr(request.state, "db_time_ms", 0.0)
            request.state.db_time_ms = round(current_db_time + db_ms, 2)


def get_auth_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    """Provide AuthService instance scoped to active DB session."""
    return container.get_auth_service(session)


def get_usage_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UsageService:
    """Provide UsageService instance scoped to active DB session."""
    return container.get_usage_service(session)


def get_voice_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VoiceService:
    """Provide VoiceService instance scoped to active DB session."""
    return container.get_voice_service(session)


def get_job_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobService:
    """Provide JobService instance scoped to active DB session."""
    return container.get_job_service(session)


def get_tts_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TtsService:
    """Provide TtsService instance scoped to active DB session."""
    return container.get_tts_service(session)


def get_webhook_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookService:
    """Provide WebhookService instance scoped to active DB session."""
    return container.get_webhook_service(session)


async def get_optional_api_key(
    request: Request,
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key_header: Annotated[str | None, Security(api_key_header_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiKey | None:
    """Attempt API key authentication, returning None if header is not present."""
    settings: Settings = request.app.state.settings
    raw_key: str | None = None

    if auth_header and auth_header.credentials:
        raw_key = auth_header.credentials.strip()
    elif api_key_header:
        raw_key = api_key_header.strip()
    elif "api_key" in request.query_params:
        raw_key = request.query_params["api_key"].strip()

    if raw_key:
        try:
            api_key = await auth_service.authenticate_key(raw_key)
            user_id = api_key.owner_id or "anonymous"
            tenant_id = api_key.owner_id or "default"
            user_id_ctx.set(user_id)
            tenant_id_ctx.set(tenant_id)
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            return api_key
        except AuthenticationError:
            if settings.ENVIRONMENT != "development":
                return None

    if settings.ENVIRONMENT == "development":
        dev_key = await auth_service.get_or_create_dev_key()
        user_id = dev_key.owner_id or settings.DEFAULT_DEV_OWNER_ID
        tenant_id = dev_key.owner_id or "default"
        user_id_ctx.set(user_id)
        tenant_id_ctx.set(tenant_id)
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        return dev_key

    return None


async def get_current_api_key(
    request: Request,
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key_header: Annotated[str | None, Security(api_key_header_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiKey:
    """Authenticate API key from Bearer token or X-API-Key header.

    In development mode, automatically falls back to the default workspace key if omitted or invalid.
    """
    settings: Settings = request.app.state.settings
    raw_key: str | None = None

    if auth_header and auth_header.credentials:
        raw_key = auth_header.credentials.strip()
    elif api_key_header:
        raw_key = api_key_header.strip()
    elif "api_key" in request.query_params:
        raw_key = request.query_params["api_key"].strip()

    if raw_key:
        try:
            api_key = await auth_service.authenticate_key(raw_key)
            user_id = api_key.owner_id or "anonymous"
            tenant_id = api_key.owner_id or "default"
            user_id_ctx.set(user_id)
            tenant_id_ctx.set(tenant_id)
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            return api_key
        except AuthenticationError:
            if settings.ENVIRONMENT != "development":
                raise

    if settings.ENVIRONMENT == "development":
        dev_key = await auth_service.get_or_create_dev_key()
        user_id = dev_key.owner_id or settings.DEFAULT_DEV_OWNER_ID
        tenant_id = dev_key.owner_id or "default"
        user_id_ctx.set(user_id)
        tenant_id_ctx.set(tenant_id)
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        return dev_key

    raise AuthenticationError(
        "API key is missing. Provide via Bearer token or X-API-Key header."
    )


# Convenient type annotations for route injection
CurrentApiKey = Annotated[ApiKey, Depends(get_current_api_key)]
OptionalApiKey = Annotated[ApiKey | None, Depends(get_optional_api_key)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UsageServiceDep = Annotated[UsageService, Depends(get_usage_service)]
VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
TtsServiceDep = Annotated[TtsService, Depends(get_tts_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
