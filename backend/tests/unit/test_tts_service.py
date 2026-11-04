"""Unit tests for TtsService and JobService."""

import pytest

from vocara.core.exceptions import QuotaExceededError, VoiceNotFoundError
from vocara.domain.entities import ApiKey, Job, Voice
from vocara.domain.enums import JobStatus, VoiceType, VoiceVisibility
from vocara.domain.ports import (
    ApiKeyRepository,
    BlobStorage,
    JobQueue,
    JobRepository,
    UsageRepository,
    VoiceRepository,
)
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.services.job_service import JobService
from vocara.services.tts_service import TtsService
from vocara.services.usage_service import UsageService


class MockVoiceRepo(VoiceRepository):
    def __init__(self) -> None:
        self.voices: dict[str, Voice] = {}

    async def get_by_id(self, voice_id: str) -> Voice | None:
        return self.voices.get(voice_id)

    async def list_accessible_voices(
        self, owner_id: str, skip: int = 0, limit: int = 50
    ) -> list[Voice]:
        return list(self.voices.values())

    async def create(self, voice: Voice) -> Voice:
        self.voices[voice.id] = voice
        return voice

    async def update(self, voice: Voice) -> Voice:
        self.voices[voice.id] = voice
        return voice

    async def delete(self, voice_id: str) -> bool:
        return self.voices.pop(voice_id, None) is not None


class MockJobRepo(JobRepository):
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}

    async def get_by_id(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def list_by_owner(self, owner_id: str, skip: int = 0, limit: int = 50) -> list[Job]:
        return [j for j in self.jobs.values() if j.owner_id == owner_id]

    async def create(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        output_audio_key: str | None = None,
        duration_seconds: float = 0.0,
        error_message: str | None = None,
    ) -> Job:
        job = self.jobs[job_id]
        job.status = status
        if output_audio_key:
            job.output_audio_key = output_audio_key
        if duration_seconds > 0:
            job.audio_duration_seconds = duration_seconds
        if error_message:
            job.error_message = error_message
        return job


class MockQueue(JobQueue):
    def __init__(self) -> None:
        self.queue: list[dict] = []

    async def enqueue(self, queue_name: str, payload: dict) -> str:
        self.queue.append(payload)
        return str(payload.get("job_id"))

    async def dequeue(self, queue_name: str, timeout_seconds: int = 10) -> dict | None:
        return self.queue.pop(0) if self.queue else None


class MockStorage(BlobStorage):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload(self, file_key: str, data: bytes, content_type: str = "audio/mpeg") -> str:
        self.files[file_key] = data
        return file_key

    async def download(self, file_key: str) -> bytes:
        if file_key in self.files:
            return self.files[file_key]
        raise FileNotFoundError(file_key)

    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str:
        return f"/download/{file_key}"

    async def delete(self, file_key: str) -> bool:
        return self.files.pop(file_key, None) is not None


class MockUsageRepo(UsageRepository):
    async def record_usage(self, record) -> None:
        pass

    async def get_monthly_usage(self, owner_id: str, year: int, month: int) -> int:
        return 0


class MockKeyRepo(ApiKeyRepository):
    def __init__(self) -> None:
        self.keys: dict[str, ApiKey] = {}

    async def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        return None

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        return self.keys.get(key_id)

    async def list_by_owner(self, owner_id: str) -> list[ApiKey]:
        return list(self.keys.values())

    async def create(self, api_key: ApiKey) -> ApiKey:
        self.keys[api_key.id] = api_key
        return api_key

    async def revoke(self, key_id: str) -> bool:
        return True

    async def increment_usage(self, key_id: str, characters: int) -> None:
        if key_id in self.keys:
            self.keys[key_id].chars_used_this_month += characters


@pytest.fixture
def tts_fixtures():
    voice_repo = MockVoiceRepo()
    job_repo = MockJobRepo()
    queue = MockQueue()
    storage = MockStorage()
    key_repo = MockKeyRepo()
    usage_service = UsageService(MockUsageRepo(), key_repo)
    job_service = JobService(job_repo=job_repo, job_queue=queue, storage=storage)
    inference = FakeInferenceEngine()

    tts_service = TtsService(
        voice_repo=voice_repo,
        usage_service=usage_service,
        inference_engine=inference,
        job_service=job_service,
        async_char_threshold=250,
    )

    api_key = ApiKey(
        id="key_1",
        key_prefix="voc_live_12345678",
        hashed_secret="secret",
        owner_id="dev_user",
        name="Test Key",
        char_quota_per_month=1000,
        chars_used_this_month=0,
    )
    key_repo.keys["key_1"] = api_key

    voice = Voice(
        id="voice_1",
        name="Sophea",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        visibility=VoiceVisibility.PUBLIC,
    )
    voice_repo.voices["voice_1"] = voice

    return tts_service, job_service, api_key, voice_repo, storage


@pytest.mark.asyncio
async def test_tts_short_text_sync_routing(tts_fixtures):
    tts_service, _, api_key, _, _ = tts_fixtures

    short_text = "ជំរាបសួរ ប្រទេសកម្ពុជា"
    audio_bytes, duration, fmt, job = await tts_service.synthesize_or_enqueue(
        api_key=api_key,
        text=short_text,
        voice_id="voice_1",
        language="km-KH",
    )

    assert audio_bytes is not None
    assert len(audio_bytes) > 0
    assert duration > 0.0
    assert fmt == "mp3"
    assert job is None


@pytest.mark.asyncio
async def test_tts_long_text_async_routing(tts_fixtures):
    tts_service, job_service, api_key, _, storage = tts_fixtures

    long_text = "ក" * 300  # 300 characters exceeds 250 threshold
    audio_bytes, duration, fmt, job = await tts_service.synthesize_or_enqueue(
        api_key=api_key,
        text=long_text,
        voice_id="voice_1",
        language="km-KH",
    )

    assert audio_bytes is None
    assert job is not None
    assert job.status == JobStatus.QUEUED
    assert job.char_count == 300

    # Complete job and retrieve audio
    await storage.upload(f"jobs/{job.id}.mp3", b"finished-audio", content_type="audio/mpeg")
    await job_service.complete_job(
        job.id, output_audio_key=f"jobs/{job.id}.mp3", duration_seconds=5.0
    )

    downloaded, media_type = await job_service.get_job_audio(job.id, owner_id="dev_user")
    assert downloaded == b"finished-audio"
    assert media_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_tts_quota_and_missing_voice(tts_fixtures):
    tts_service, _, api_key, _, _ = tts_fixtures

    # Exceed quota
    api_key.chars_used_this_month = 950
    with pytest.raises(QuotaExceededError):
        await tts_service.synthesize_or_enqueue(
            api_key=api_key,
            text="Text longer than fifty characters to intentionally exceed remaining quota",
            voice_id="voice_1",
        )

    # Missing voice
    with pytest.raises(VoiceNotFoundError):
        await tts_service.synthesize_or_enqueue(
            api_key=api_key,
            text="Hello",
            voice_id="non_existent_voice",
        )
