"""Unit tests for voice cloning, consent verification, and voice design logic."""

import pytest

from vocara.core.exceptions import (
    ConsentRequiredError,
    InvalidAudioError,
    VoiceNotFoundError,
)
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.domain.ports import BlobStorage, VoiceRepository
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.services.voice_service import VoiceService
from vocara.utils.audio import generate_synthetic_tone_wav


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
        if file_key not in self.data:
            raise FileNotFoundError(f"Key {file_key} not found")
        return self.data[file_key]

    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str:
        return f"https://mock-storage.local/{file_key}"

    async def delete(self, file_key: str) -> bool:
        return bool(self.data.pop(file_key, None))


@pytest.fixture
def voice_repo() -> InMemoryVoiceRepo:
    return InMemoryVoiceRepo()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def fake_engine() -> FakeInferenceEngine:
    return FakeInferenceEngine()


@pytest.fixture
def voice_service(
    voice_repo: InMemoryVoiceRepo,
    storage: InMemoryStorage,
    fake_engine: FakeInferenceEngine,
) -> VoiceService:
    return VoiceService(voice_repo=voice_repo, storage=storage, inference_engine=fake_engine)


@pytest.mark.asyncio
async def test_clone_voice_requires_consent(voice_service: VoiceService) -> None:
    """Cloning must raise ConsentRequiredError when consent_confirmed is False."""
    sample_wav = generate_synthetic_tone_wav(duration_seconds=1.0)

    with pytest.raises(ConsentRequiredError) as exc_info:
        await voice_service.clone_voice(
            owner_id="dev_user_1",
            name="Unconsented Voice",
            audio_bytes=sample_wav,
            consent_confirmed=False,
        )

    assert exc_info.value.code == "CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_clone_voice_invalid_audio_fails(voice_service: VoiceService) -> None:
    """Cloning with corrupt or non-audio bytes raises InvalidAudioError."""
    corrupted_bytes = b"NOT_A_VALID_AUDIO_FILE_DATA"

    with pytest.raises(InvalidAudioError) as exc_info:
        await voice_service.clone_voice(
            owner_id="dev_user_1",
            name="Corrupted Voice",
            audio_bytes=corrupted_bytes,
            consent_confirmed=True,
        )

    assert exc_info.value.code == "INVALID_AUDIO"


@pytest.mark.asyncio
async def test_clone_voice_success(voice_service: VoiceService, storage: InMemoryStorage) -> None:
    """Successful cloning uploads reference/preview audio and verifies consent metadata."""
    sample_wav = generate_synthetic_tone_wav(duration_seconds=1.2, sample_rate=24000)

    voice = await voice_service.clone_voice(
        owner_id="dev_user_1",
        name="Cloned Voice 1",
        audio_bytes=sample_wav,
        consent_confirmed=True,
        language="km-KH",
        description="A verified cloned voice profile",
    )

    assert voice.id is not None
    assert voice.voice_type == VoiceType.CLONED
    assert voice.owner_id == "dev_user_1"
    assert voice.language == "km-KH"
    assert voice.modifiers["consent_verified"] is True
    assert "consent_timestamp" in voice.modifiers
    assert "feature_token" in voice.modifiers

    # Verify storage upload
    assert voice.reference_audio_key in storage.data
    assert voice.preview_audio_key in storage.data


@pytest.mark.asyncio
async def test_design_voice_success(
    voice_service: VoiceService, voice_repo: InMemoryVoiceRepo
) -> None:
    """Designing a variation from an accessible base voice records modifier overrides."""
    base_voice = Voice(
        id="base_builtin_1",
        name="Base Voice",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        description="Standard system base voice",
        visibility=VoiceVisibility.PUBLIC,
    )
    await voice_repo.create(base_voice)

    designed = await voice_service.design_voice(
        owner_id="dev_user_1",
        name="Designed Variation",
        base_voice_id="base_builtin_1",
        pitch=1.2,
        speed=0.9,
        emotion="cheerful",
        style="narrative",
    )

    assert designed.id is not None
    assert designed.voice_type == VoiceType.DESIGNED
    assert designed.owner_id == "dev_user_1"
    assert designed.modifiers["parent_voice_id"] == "base_builtin_1"
    assert designed.modifiers["pitch"] == 1.2
    assert designed.modifiers["speed"] == 0.9
    assert designed.modifiers["emotion"] == "cheerful"
    assert designed.modifiers["style"] == "narrative"
    assert "feature_token" in designed.modifiers


@pytest.mark.asyncio
async def test_design_voice_inaccessible_base_fails(
    voice_service: VoiceService, voice_repo: InMemoryVoiceRepo
) -> None:
    """Cannot design a voice variation based on another developer's private voice."""
    private_other_voice = Voice(
        id="private_other_voice",
        name="Private Voice Other Dev",
        voice_type=VoiceType.CLONED,
        owner_id="other_user_2",
        language="km-KH",
        visibility=VoiceVisibility.PRIVATE,
    )
    await voice_repo.create(private_other_voice)

    with pytest.raises(VoiceNotFoundError):
        await voice_service.design_voice(
            owner_id="dev_user_1",
            name="Illegitimate Child Voice",
            base_voice_id="private_other_voice",
        )
