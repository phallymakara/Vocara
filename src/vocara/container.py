"""Dependency Injection Container (Composition Root).

Wires infrastructure adapters to domain services in a single, predictable location.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vocara.core.config import Settings
from vocara.domain.ports import (
    ApiKeyRepository,
    BlobStorage,
    InferenceEngine,
    JobQueue,
    JobRepository,
    UsageRepository,
    VoiceRepository,
    WebhookRepository,
)
from vocara.infrastructure.db.repositories.api_key_repo import SqlApiKeyRepository
from vocara.infrastructure.db.repositories.job_repo import SqlJobRepository
from vocara.infrastructure.db.repositories.usage_repo import SqlUsageRepository
from vocara.infrastructure.db.repositories.voice_repo import SqlVoiceRepository
from vocara.infrastructure.db.repositories.webhook_repo import SqlWebhookRepository
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.infrastructure.inference.modal_engine import ModalInferenceEngine
from vocara.infrastructure.queue.redis_queue import RedisJobQueue
from vocara.infrastructure.storage.local import LocalStorageAdapter
from vocara.services.auth_service import AuthService
from vocara.services.job_service import JobService
from vocara.services.tts_service import TtsService
from vocara.services.usage_service import UsageService
from vocara.services.voice_service import VoiceService
from vocara.services.webhook_service import WebhookService


class Container:
    """Application Composition Root managing instances and adapter lifecycles."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_engine: Any = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.storage: BlobStorage | None = None
        self.inference_engine: InferenceEngine | None = None
        self.job_queue: JobQueue | None = None

    async def initialize(self) -> None:
        """Initialize connection pools, storage directories, and clients."""
        from vocara.infrastructure.db.session import create_engine, create_session_factory

        self.db_engine = create_engine(self.settings)
        self.session_factory = create_session_factory(self.db_engine)

        # Storage initialization
        if self.settings.STORAGE_BACKEND == "local":
            self.storage = LocalStorageAdapter(self.settings.LOCAL_STORAGE_DIR)

        # Queue initialization
        self.job_queue = RedisJobQueue(self.settings.REDIS_URL)

        # Inference engine initialization
        if self.settings.INFERENCE_ENGINE_TYPE == "modal" and self.settings.MODAL_API_ENDPOINT:
            self.inference_engine = ModalInferenceEngine(
                endpoint_url=self.settings.MODAL_API_ENDPOINT,
                api_token=self.settings.MODAL_API_TOKEN,
                timeout_seconds=self.settings.INFERENCE_TIMEOUT_SECONDS,
            )
        else:
            self.inference_engine = FakeInferenceEngine()

    async def shutdown(self) -> None:
        """Gracefully release connections and background tasks."""
        if self.db_engine:
            await self.db_engine.dispose()

    # Repository Factory Methods
    def get_api_key_repo(self, session: AsyncSession) -> ApiKeyRepository:
        """Return ApiKeyRepository port adapter bound to session."""
        return SqlApiKeyRepository(session)

    def get_voice_repo(self, session: AsyncSession) -> VoiceRepository:
        """Return VoiceRepository port adapter bound to session."""
        return SqlVoiceRepository(session)

    def get_job_repo(self, session: AsyncSession) -> JobRepository:
        """Return JobRepository port adapter bound to session."""
        return SqlJobRepository(session)

    def get_usage_repo(self, session: AsyncSession) -> UsageRepository:
        """Return UsageRepository port adapter bound to session."""
        return SqlUsageRepository(session)

    def get_webhook_repo(self, session: AsyncSession) -> WebhookRepository:
        """Return WebhookRepository port adapter bound to session."""
        return SqlWebhookRepository(session)

    # Domain Services Factory Methods
    def get_auth_service(self, session: AsyncSession) -> AuthService:
        """Return AuthService wired with ApiKeyRepository and application settings."""
        return AuthService(self.get_api_key_repo(session), self.settings)

    def get_usage_service(self, session: AsyncSession) -> UsageService:
        """Return UsageService wired with UsageRepository and ApiKeyRepository."""
        return UsageService(self.get_usage_repo(session), self.get_api_key_repo(session))

    def get_voice_service(self, session: AsyncSession) -> VoiceService:
        """Return VoiceService wired with VoiceRepository, BlobStorage, and InferenceEngine."""
        inference = self.inference_engine or FakeInferenceEngine()
        return VoiceService(self.get_voice_repo(session), self.storage, inference)

    def get_job_service(self, session: AsyncSession) -> JobService:
        """Return JobService wired with JobRepository, JobQueue, and BlobStorage."""
        return JobService(
            job_repo=self.get_job_repo(session),
            job_queue=self.job_queue,
            storage=self.storage,
        )

    def get_tts_service(self, session: AsyncSession) -> TtsService:
        """Return TtsService wired with VoiceRepository, UsageService, InferenceEngine,
        and JobService.
        """
        inference = self.inference_engine or FakeInferenceEngine()
        return TtsService(
            voice_repo=self.get_voice_repo(session),
            usage_service=self.get_usage_service(session),
            inference_engine=inference,
            job_service=self.get_job_service(session),
        )

    def get_webhook_service(self, session: AsyncSession) -> WebhookService:
        """Return WebhookService wired with WebhookRepository."""
        return WebhookService(self.get_webhook_repo(session))
