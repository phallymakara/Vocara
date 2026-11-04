"""Unit tests for VoiceService and audio normalization utilities."""

import pytest

from vocara.core.exceptions import AuthorizationError, VoiceNotFoundError
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.domain.ports import BlobStorage, VoiceRepository
from vocara.services.voice_service import VoiceService
from vocara.utils.audio import (
    generate_synthetic_tone_wav,
    get_audio_duration_seconds,
    normalize_audio_to_wav,
    validate_reference_audio,
)


class InMemoryVoiceRepo(VoiceRepository):
    """In-memory mock for VoiceRepository."""

    def __init__(self) -> None:
        self.voices: dict[str, Voice] = {}

    async def get_by_id(self, voice_id: str) -> Voice | None:
        return self.voices.get(voice_id)

    async def list_accessible_voices(
        self, owner_id: str, skip: int = 0, limit: int = 50
    ) -> list[Voice]:
        return [
            v
            for v in self.voices.values()
            if v.is_active and (v.owner_id == owner_id or v.visibility == VoiceVisibility.PUBLIC)
        ]

    async def create(self, voice: Voice) -> Voice:
        self.voices[voice.id] = voice
        return voice

    async def update(self, voice: Voice) -> Voice:
        self.voices[voice.id] = voice
        return voice

    async def delete(self, voice_id: str) -> bool:
        if voice_id in self.voices:
            self.voices[voice_id].is_active = False
            return True
        return False


class InMemoryStorage(BlobStorage):
    """In-memory storage mock."""

    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def upload(self, file_key: str, data: bytes, content_type: str = "audio/mpeg") -> str:
        self.data[file_key] = data
        return file_key

    async def download(self, file_key: str) -> bytes:
        if file_key in self.data:
            return self.data[file_key]
        raise FileNotFoundError(file_key)

    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str:
        return f"/storage/{file_key}"

    async def delete(self, file_key: str) -> bool:
        return self.data.pop(file_key, None) is not None


@pytest.fixture
def voice_repo() -> InMemoryVoiceRepo:
    repo = InMemoryVoiceRepo()
    # Built-in public voice
    repo.voices["builtin_1"] = Voice(
        id="builtin_1",
        name="Sophea (Built-in)",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        visibility=VoiceVisibility.PUBLIC,
    )
    # Private custom voice for user 1
    repo.voices["custom_1"] = Voice(
        id="custom_1",
        name="User 1 Voice",
        voice_type=VoiceType.CLONED,
        owner_id="user_1",
        language="km-KH",
        visibility=VoiceVisibility.PRIVATE,
    )
    # Private custom voice for user 2
    repo.voices["custom_2"] = Voice(
        id="custom_2",
        name="User 2 Voice",
        voice_type=VoiceType.CLONED,
        owner_id="user_2",
        language="km-KH",
        visibility=VoiceVisibility.PRIVATE,
    )
    return repo


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def voice_service(voice_repo: InMemoryVoiceRepo, storage: InMemoryStorage) -> VoiceService:
    return VoiceService(voice_repo, storage)


@pytest.mark.asyncio
async def test_voice_listing_and_filtering(voice_service: VoiceService) -> None:
    # user_1 should see builtin_1 and custom_1, but not custom_2
    voices = await voice_service.list_voices(owner_id="user_1")
    ids = [v.id for v in voices]
    assert "builtin_1" in ids
    assert "custom_1" in ids
    assert "custom_2" not in ids

    # Filter by voice_type
    cloned = await voice_service.list_voices(owner_id="user_1", voice_type=VoiceType.CLONED)
    assert len(cloned) == 1
    assert cloned[0].id == "custom_1"


@pytest.mark.asyncio
async def test_voice_tenancy_isolation(voice_service: VoiceService) -> None:
    # user_1 accessing user_2 private voice should raise VoiceNotFoundError
    with pytest.raises(VoiceNotFoundError):
        await voice_service.get_voice_by_id("custom_2", owner_id="user_1")


@pytest.mark.asyncio
async def test_update_and_delete_permissions(voice_service: VoiceService) -> None:
    # Built-in cannot be modified or deleted
    with pytest.raises(AuthorizationError):
        await voice_service.update_voice("builtin_1", owner_id="user_1", name="Hacked Name")

    with pytest.raises(AuthorizationError):
        await voice_service.delete_voice("builtin_1", owner_id="user_1")

    # Custom voice update succeeds for owner
    updated = await voice_service.update_voice(
        "custom_1", owner_id="user_1", name="User 1 Renamed", description="New description"
    )
    assert updated.name == "User 1 Renamed"
    assert updated.description == "New description"

    # Custom voice delete succeeds for owner
    deleted = await voice_service.delete_voice("custom_1", owner_id="user_1")
    assert deleted is True


@pytest.mark.asyncio
async def test_preview_stream(voice_service: VoiceService, storage: InMemoryStorage) -> None:
    # Store audio for preview
    await storage.upload("previews/sample.wav", b"fake-audio-bytes", content_type="audio/wav")
    voice = await voice_service.get_voice_by_id("builtin_1", owner_id="user_1")
    voice.preview_audio_key = "previews/sample.wav"

    audio, content_type = await voice_service.get_preview_stream("builtin_1", owner_id="user_1")
    assert audio == b"fake-audio-bytes"
    assert content_type == "audio/wav"


def test_audio_normalization_and_duration() -> None:
    # Generate 1.0 second synthetic audio at 16kHz
    sample_wav = generate_synthetic_tone_wav(
        duration_seconds=1.0, sample_rate=16000, frequency=440.0
    )

    # Validate reference audio
    validated = validate_reference_audio(sample_wav)
    assert validated["format"] == "wav"

    # Duration check
    duration = get_audio_duration_seconds(sample_wav)
    assert pytest.approx(duration, rel=1e-2) == 1.0

    # Normalize to 24kHz
    normalized_wav, norm_duration = normalize_audio_to_wav(sample_wav, target_sample_rate=24000)
    assert len(normalized_wav) > 0
    assert pytest.approx(norm_duration, rel=1e-2) == 1.0
