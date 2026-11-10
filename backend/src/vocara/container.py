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
from vocara.infrastructure.inference.huggingface_engine import HuggingFaceInferenceEngine
from vocara.infrastructure.inference.modal_engine import ModalInferenceEngine
from vocara.infrastructure.queue.redis_queue import RedisJobQueue
from vocara.infrastructure.storage.azure import AzureBlobStorageAdapter
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

        # Auto-create tables and seed voices for local SQLite development
        if str(self.settings.DATABASE_URL).startswith("sqlite"):
            from vocara.infrastructure.db.models import Base
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            from vocara.domain.entities import Voice
            from vocara.domain.enums import VoiceType, VoiceVisibility
            from vocara.infrastructure.db.repositories.voice_repo import SqlVoiceRepository

            voice_repo = SqlVoiceRepository(session)
            seed_items = self.settings.DEFAULT_SEED_VOICES
            for item in seed_items:
                voice_id = str(item.get("id", "")).strip()
                if not voice_id:
                    continue
                seed_modifiers = dict(item.get("modifiers") or {})
                existing = await voice_repo.get_by_id(voice_id)
                if not existing:
                    await voice_repo.create(
                        Voice(
                            id=voice_id,
                            name=str(item.get("name", voice_id)),
                            voice_type=VoiceType.BUILT_IN,
                            owner_id=None,
                            language=str(item.get("language", "km-KH")),
                            visibility=VoiceVisibility.PUBLIC,
                            description=str(item.get("description", "")),
                            reference_audio_key=item.get("reference_audio_key"),
                            preview_audio_key=item.get("preview_audio_key"),
                            modifiers=seed_modifiers,
                        )
                    )
                else:
                    # Clean legacy non-built-in reference keys or missing control_instruction on built-ins
                    needs_update = False
                    expected_prefix = f"voices/{voice_id}/"
                    if (
                        existing.voice_type == VoiceType.BUILT_IN
                        and existing.reference_audio_key
                        and not existing.reference_audio_key.startswith(expected_prefix)
                    ):
                        existing.reference_audio_key = item.get("reference_audio_key")
                        existing.preview_audio_key = item.get("preview_audio_key")
                        needs_update = True
                    if seed_modifiers and "control_instruction" not in (existing.modifiers or {}):
                        existing.modifiers = {**(existing.modifiers or {}), **seed_modifiers}
                        needs_update = True
                    if needs_update:
                        await voice_repo.update(existing)
            await session.commit()

        # Storage initialization
        if self.settings.STORAGE_BACKEND == "azure" and self.settings.AZURE_STORAGE_CONNECTION_STRING:
            self.storage = AzureBlobStorageAdapter(
                connection_string=self.settings.AZURE_STORAGE_CONNECTION_STRING,
                container_name=self.settings.AZURE_STORAGE_CONTAINER_NAME,
            )
        else:
            self.storage = LocalStorageAdapter(self.settings.LOCAL_STORAGE_DIR)

        # Queue initialization
        self.job_queue = RedisJobQueue(self.settings.REDIS_URL)

        # Inference engine initialization (no edge_tts fallback)
        fake_fallback = FakeInferenceEngine(
            sample_rate=self.settings.AUDIO_SAMPLE_RATE_HZ,
            storage=self.storage,
        )

        if self.settings.INFERENCE_ENGINE_TYPE == "fake":
            self.inference_engine = fake_fallback
        elif self.settings.INFERENCE_ENGINE_TYPE == "modal":
            if not self.settings.MODAL_API_ENDPOINT:
                raise ValueError("MODAL_API_ENDPOINT must be configured when INFERENCE_ENGINE_TYPE=modal.")
            self.inference_engine = ModalInferenceEngine(
                endpoint_url=self.settings.MODAL_API_ENDPOINT,
                api_token=self.settings.MODAL_API_TOKEN,
                timeout_seconds=self.settings.INFERENCE_TIMEOUT_SECONDS,
                storage=self.storage,
                inference_timesteps=self.settings.VOXCPM_INFERENCE_TIMESTEPS,
                cfg_value=self.settings.VOXCPM_CFG_VALUE,
                max_chunk_chars=self.settings.VOXCPM_MAX_CHUNK_CHARS,
                default_km_preview=self.settings.DEFAULT_PREVIEW_TEXT_KM,
                default_en_preview=self.settings.DEFAULT_PREVIEW_TEXT_EN,
            )
        elif self.settings.INFERENCE_ENGINE_TYPE == "huggingface":
            self.inference_engine = HuggingFaceInferenceEngine(
                endpoint_url=self.settings.HUGGINGFACE_ENDPOINT_URL,
                api_token=self.settings.HUGGINGFACE_API_KEY,
                model_id=self.settings.HUGGINGFACE_MODEL_ID,
                timeout_seconds=self.settings.INFERENCE_TIMEOUT_SECONDS,
                storage=self.storage,
            )
        else:
            self.inference_engine = fake_fallback

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
        inference = self.inference_engine or FakeInferenceEngine(
            sample_rate=self.settings.AUDIO_SAMPLE_RATE_HZ
        )
        return VoiceService(
            self.get_voice_repo(session),
            self.storage,
            inference,
            sample_rate=self.settings.AUDIO_SAMPLE_RATE_HZ,
            default_km_preview=self.settings.DEFAULT_PREVIEW_TEXT_KM,
            default_en_preview=self.settings.DEFAULT_PREVIEW_TEXT_EN,
        )

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
            async_char_threshold=getattr(self.settings, "ASYNC_CHAR_THRESHOLD", 2000),
        )

    def get_webhook_service(self, session: AsyncSession) -> WebhookService:
        """Return WebhookService wired with WebhookRepository."""
        return WebhookService(self.get_webhook_repo(session))
