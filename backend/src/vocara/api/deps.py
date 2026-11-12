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
from vocara.core.security import verify_access_token
from vocara.domain.entities import ApiKey, User
from vocara.services.auth_service import AuthService
from vocara.services.job_service import JobService
from vocara.services.tts_service import TtsService
from vocara.services.usage_service import UsageService
from vocara.services.user_auth_service import UserAuthService
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


def get_user_auth_service(
    container: Annotated[Container, Depends(get_container)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserAuthService:
    """Provide UserAuthService instance scoped to active DB session."""
    return container.get_user_auth_service(session)


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


async def get_current_user(
    request: Request,
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    user_auth_service: Annotated[UserAuthService, Depends(get_user_auth_service)],
) -> User:
    """Authenticate a user via Bearer JWT session token."""
    settings: Settings = request.app.state.settings
    token = auth_header.credentials.strip() if auth_header and auth_header.credentials else None
    if not token:
        raise AuthenticationError("Authentication required. Please log in.")

    payload = verify_access_token(token, settings.SECRET_KEY)
    if not payload or not payload.get("sub"):
        raise AuthenticationError("Session expired or invalid. Please log in again.")

    user = await user_auth_service.user_repo.get_by_id(str(payload["sub"]))
    if not user or not user.is_active:
        raise AuthenticationError("Account is unavailable or inactive.")

    user_id_ctx.set(user.id)
    tenant_id_ctx.set(user.id)
    request.state.user_id = user.id
    request.state.tenant_id = user.id
    return user


async def _authenticate_raw_bearer(
    raw_token: str,
    settings: Settings,
    auth_service: AuthService,
    user_auth_service: UserAuthService,
) -> ApiKey:
    """Authenticate either an API key (voc_live_/voc_test_) or a user JWT session."""
    if raw_token.startswith("voc_live_") or raw_token.startswith("voc_test_"):
        return await auth_service.authenticate_key(raw_token)

    payload = verify_access_token(raw_token, settings.SECRET_KEY)
    if payload and payload.get("sub"):
        user = await user_auth_service.user_repo.get_by_id(str(payload["sub"]))
        if not user or not user.is_active:
            raise AuthenticationError("Account is unavailable or inactive.")
        return await user_auth_service.ensure_active_api_key(user)

    raise AuthenticationError("Invalid authentication credentials.")


async def get_optional_api_key(
    request: Request,
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key_header: Annotated[str | None, Security(api_key_header_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_auth_service: Annotated[UserAuthService, Depends(get_user_auth_service)],
) -> ApiKey | None:
    """Attempt API key or JWT authentication, returning None if header is not present."""
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
            api_key = await _authenticate_raw_bearer(
                raw_key, settings, auth_service, user_auth_service
            )
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
    user_auth_service: Annotated[UserAuthService, Depends(get_user_auth_service)],
) -> ApiKey:
    """Authenticate via API key (Bearer/X-API-Key/?api_key=) or user JWT session.

    In development mode, falls back to the default workspace key if omitted or non-JWT.
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
        is_jwt_shape = raw_key.count(".") == 2 and not raw_key.startswith("voc_")
        try:
            api_key = await _authenticate_raw_bearer(
                raw_key, settings, auth_service, user_auth_service
            )
            user_id = api_key.owner_id or "anonymous"
            tenant_id = api_key.owner_id or "default"
            user_id_ctx.set(user_id)
            tenant_id_ctx.set(tenant_id)
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            return api_key
        except AuthenticationError:
            if settings.ENVIRONMENT != "development" or is_jwt_shape:
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
CurrentUser = Annotated[User, Depends(get_current_user)]
UserAuthServiceDep = Annotated[UserAuthService, Depends(get_user_auth_service)]
CurrentApiKey = Annotated[ApiKey, Depends(get_current_api_key)]
OptionalApiKey = Annotated[ApiKey | None, Depends(get_optional_api_key)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UsageServiceDep = Annotated[UsageService, Depends(get_usage_service)]
VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
TtsServiceDep = Annotated[TtsService, Depends(get_tts_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
