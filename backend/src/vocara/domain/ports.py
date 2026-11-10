"""Domain ports (interfaces) defining boundary contracts.

These protocols define contracts implemented by the infrastructure adapters.
"""

from typing import Any, Protocol, runtime_checkable

from vocara.domain.entities import ApiKey, Job, UsageRecord, Voice, WebhookSubscription
from vocara.domain.enums import AudioFormat, JobStatus


@runtime_checkable
class VoiceRepository(Protocol):
    """Storage port for Voice domain entities."""

    async def get_by_id(self, voice_id: str) -> Voice | None: ...
    async def list_accessible_voices(
        self, owner_id: str, skip: int = 0, limit: int = 50
    ) -> list[Voice]: ...
    async def create(self, voice: Voice) -> Voice: ...
    async def update(self, voice: Voice) -> Voice: ...
    async def delete(self, voice_id: str) -> bool: ...


@runtime_checkable
class JobRepository(Protocol):
    """Storage port for Job lifecycle entities."""

    async def get_by_id(self, job_id: str) -> Job | None: ...
    async def list_by_owner(self, owner_id: str, skip: int = 0, limit: int = 50) -> list[Job]: ...
    async def create(self, job: Job) -> Job: ...
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        output_audio_key: str | None = None,
        duration_seconds: float = 0.0,
        error_message: str | None = None,
    ) -> Job: ...


@runtime_checkable
class ApiKeyRepository(Protocol):
    """Storage port for developer API key credentials and quotas."""

    async def get_by_prefix(self, key_prefix: str) -> ApiKey | None: ...
    async def get_by_id(self, key_id: str) -> ApiKey | None: ...
    async def list_by_owner(self, owner_id: str) -> list[ApiKey]: ...
    async def create(self, api_key: ApiKey) -> ApiKey: ...
    async def revoke(self, key_id: str) -> bool: ...
    async def increment_usage(self, key_id: str, characters: int) -> None: ...


@runtime_checkable
class UsageRepository(Protocol):
    """Storage port for metering and audit logs."""

    async def record_usage(self, record: UsageRecord) -> None: ...
    async def get_monthly_usage(self, owner_id: str, year: int, month: int) -> int: ...


@runtime_checkable
class WebhookRepository(Protocol):
    """Storage port for developer webhooks."""

    async def get_by_id(self, subscription_id: str) -> WebhookSubscription | None: ...
    async def get_by_owner(self, owner_id: str) -> list[WebhookSubscription]: ...
    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription: ...
    async def delete(self, subscription_id: str) -> bool: ...


@runtime_checkable
class BlobStorage(Protocol):
    """Port for audio object storage (Azure Blob, Cloudflare R2, Local)."""

    async def upload(self, file_key: str, data: bytes, content_type: str = "audio/mpeg") -> str: ...
    async def download(self, file_key: str) -> bytes: ...
    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str: ...
    async def delete(self, file_key: str) -> bool: ...


@runtime_checkable
class InferenceEngine(Protocol):
    """Port for AI voice synthesis, voice cloning, and voice design."""

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str,
        speed: float,
        output_format: AudioFormat,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Synthesize text to speech audio bytes and return (audio_bytes, duration_seconds)."""
        ...

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str,
    ) -> tuple[str, bytes] | tuple[str, bytes, str]:
        """Process reference audio and return (reference_features_token, sample_audio_bytes[, detected_prompt])."""
        ...

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
        preview_text: str | None = None,
    ) -> tuple[str, bytes]:
        """Create a voice variation and return (derived_features_token, preview_audio_bytes)."""
        ...


@runtime_checkable
class JobQueue(Protocol):
    """Port for asynchronous job scheduling."""

    async def enqueue(self, queue_name: str, payload: dict[str, Any]) -> str: ...
    async def dequeue(
        self, queue_name: str, timeout_seconds: int = 10
    ) -> dict[str, Any] | None: ...


@runtime_checkable
class WebhookDispatcher(Protocol):
    """Port for asynchronously notifying external developer URLs."""

    async def dispatch(
        self, url: str, secret: str, event_type: str, data: dict[str, Any]
    ) -> bool: ...
