"""Domain enumerations for the Vocara Voice API Platform."""

from enum import StrEnum


class VoiceType(StrEnum):
    """Categorization of voices in the system."""

    BUILT_IN = "built_in"
    CLONED = "cloned"
    DESIGNED = "designed"


class VoiceVisibility(StrEnum):
    """Access visibility for voice entities."""

    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


class JobType(StrEnum):
    """Types of asynchronous or synchronous inference jobs."""

    TTS_REALTIME = "tts_realtime"
    TTS_BATCH = "tts_batch"
    VOICE_CLONE = "voice_clone"
    VOICE_DESIGN = "voice_design"


class JobStatus(StrEnum):
    """Lifecycle status of an inference job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioFormat(StrEnum):
    """Supported audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"


class ApiKeyStatus(StrEnum):
    """Status of developer API authentication keys."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
