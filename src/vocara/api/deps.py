"""FastAPI dependency providers for authentication, database sessions, and services."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.container import Container
from vocara.core.exceptions import AuthenticationError
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
    container: Annotated[Container, Depends(get_container)],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide scoped async database session."""
    if not container.session_factory:
        raise RuntimeError("Database session factory is not initialized.")

    async with container.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key_header: Annotated[str | None, Security(api_key_header_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiKey | None:
    """Attempt API key authentication, returning None if header is not present."""
    raw_key: str | None = None

    if auth_header and auth_header.credentials:
        raw_key = auth_header.credentials.strip()
    elif api_key_header:
        raw_key = api_key_header.strip()

    if not raw_key:
        return None

    try:
        return await auth_service.authenticate_key(raw_key)
    except AuthenticationError:
        return None


async def get_current_api_key(
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key_header: Annotated[str | None, Security(api_key_header_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiKey:
    """Authenticate API key from Bearer token or X-API-Key header.

    Raises:
        AuthenticationError: If header is missing or key is invalid.
    """
    raw_key: str | None = None

    if auth_header and auth_header.credentials:
        raw_key = auth_header.credentials.strip()
    elif api_key_header:
        raw_key = api_key_header.strip()

    if not raw_key:
        raise AuthenticationError(
            "API key is missing. Provide via Bearer token or X-API-Key header."
        )

    return await auth_service.authenticate_key(raw_key)


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
