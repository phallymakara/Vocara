"""Pure domain entities for Vocara platform.

These models have no framework dependencies (no FastAPI, no SQLAlchemy).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vocara.domain.enums import (
    ApiKeyStatus,
    AudioFormat,
    JobStatus,
    JobType,
    VoiceType,
    VoiceVisibility,
)


@dataclass
class Voice:
    """Core domain representation of a voice profile."""

    id: str
    name: str
    voice_type: VoiceType
    owner_id: str | None
    language: str
    description: str = ""
    reference_audio_key: str | None = None
    preview_audio_key: str | None = None
    modifiers: dict[str, Any] = field(default_factory=dict)
    visibility: VoiceVisibility = VoiceVisibility.PRIVATE
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Job:
    """Represents a speech generation or voice processing job."""

    id: str
    job_type: JobType
    status: JobStatus
    owner_id: str
    voice_id: str | None = None
    input_text: str | None = None
    char_count: int = 0
    language: str = "km-KH"
    speed: float = 1.0
    output_format: AudioFormat = AudioFormat.MP3
    output_audio_key: str | None = None
    audio_duration_seconds: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApiKey:
    """Developer API key metadata and quota constraints."""

    id: str
    key_prefix: str
    hashed_secret: str
    owner_id: str
    name: str
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    rate_limit_per_minute: int = 60
    char_quota_per_month: int = 100000
    chars_used_this_month: int = 0
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def has_quota(self, chars: int) -> bool:
        """Check if character quota is sufficient."""
        return (self.chars_used_this_month + chars) <= self.char_quota_per_month


@dataclass
class UsageRecord:
    """Metering record for API billing and analytics."""

    id: str
    api_key_id: str
    owner_id: str
    job_id: str | None
    operation: str
    characters_processed: int
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookSubscription:
    """Webhook callback registered by developers."""

    id: str
    owner_id: str
    url: str
    secret: str
    event_types: list[str]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
