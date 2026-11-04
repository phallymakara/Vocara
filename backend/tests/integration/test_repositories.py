"""Integration tests for database repositories and storage adapter."""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import ApiKey, Job, UsageRecord, Voice
from vocara.domain.enums import (
    ApiKeyStatus,
    AudioFormat,
    JobStatus,
    JobType,
    VoiceType,
    VoiceVisibility,
)
from vocara.infrastructure.db.repositories.api_key_repo import SqlApiKeyRepository
from vocara.infrastructure.db.repositories.job_repo import SqlJobRepository
from vocara.infrastructure.db.repositories.usage_repo import SqlUsageRepository
from vocara.infrastructure.db.repositories.voice_repo import SqlVoiceRepository
from vocara.infrastructure.storage.local import LocalStorageAdapter


@pytest.mark.asyncio
async def test_api_key_repository(async_session: AsyncSession) -> None:
    """Test ApiKeyRepository creation, indexed prefix lookup, quota increment, and revocation."""
    repo = SqlApiKeyRepository(async_session)

    api_key = ApiKey(
        id="key-uuid-1",
        key_prefix="voc_live_12345678",
        hashed_secret="abc123hashedsecret",
        owner_id="developer_1",
        name="Production Key",
        status=ApiKeyStatus.ACTIVE,
        rate_limit_per_minute=60,
        char_quota_per_month=50000,
        chars_used_this_month=1000,
    )

    created = await repo.create(api_key)
    assert created.id == "key-uuid-1"
    assert created.key_prefix == "voc_live_12345678"

    # Query by prefix
    fetched = await repo.get_by_prefix("voc_live_12345678")
    assert fetched is not None
    assert fetched.name == "Production Key"
    assert fetched.has_quota(10000) is True

    # Increment character usage
    await repo.increment_usage("key-uuid-1", 5000)
    updated = await repo.get_by_id("key-uuid-1")
    assert updated is not None
    assert updated.chars_used_this_month == 6000

    # Revoke key
    revoked = await repo.revoke("key-uuid-1")
    assert revoked is True

    # Revoked key should no longer be returned by get_by_prefix (active only)
    active_lookup = await repo.get_by_prefix("voc_live_12345678")
    assert active_lookup is None


@pytest.mark.asyncio
async def test_voice_repository(async_session: AsyncSession) -> None:
    """Test VoiceRepository CRUD and multi-tenant visibility isolation."""
    repo = SqlVoiceRepository(async_session)

    # 1. Built-in voice (public)
    builtin_voice = Voice(
        id="voice-builtin-1",
        name="Sophea (Built-in)",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        visibility=VoiceVisibility.PUBLIC,
    )
    await repo.create(builtin_voice)

    # 2. Private voice owned by user_A
    user_a_voice = Voice(
        id="voice-usera-1",
        name="User A Custom Voice",
        voice_type=VoiceType.CLONED,
        owner_id="user_A",
        language="km-KH",
        visibility=VoiceVisibility.PRIVATE,
    )
    await repo.create(user_a_voice)

    # 3. Private voice owned by user_B
    user_b_voice = Voice(
        id="voice-userb-1",
        name="User B Custom Voice",
        voice_type=VoiceType.CLONED,
        owner_id="user_B",
        language="km-KH",
        visibility=VoiceVisibility.PRIVATE,
    )
    await repo.create(user_b_voice)

    # User A listing: should see built-in + User A's private voice, but NOT User B's voice
    accessible_a = await repo.list_accessible_voices("user_A")
    voice_ids_a = [v.id for v in accessible_a]
    assert "voice-builtin-1" in voice_ids_a
    assert "voice-usera-1" in voice_ids_a
    assert "voice-userb-1" not in voice_ids_a

    # Update User A's voice name
    user_a_voice.name = "User A Renamed"
    updated = await repo.update(user_a_voice)
    assert updated.name == "User A Renamed"

    # Soft-delete User A's voice
    deleted = await repo.delete("voice-usera-1")
    assert deleted is True

    # Once deleted, get_by_id returns None
    assert await repo.get_by_id("voice-usera-1") is None


@pytest.mark.asyncio
async def test_job_repository(async_session: AsyncSession) -> None:
    """Test JobRepository lifecycle state transitions and retrieval."""
    repo = SqlJobRepository(async_session)

    job = Job(
        id="job-uuid-100",
        job_type=JobType.TTS_BATCH,
        status=JobStatus.QUEUED,
        owner_id="dev_user",
        input_text="ជំរាបសួរ ប្រទេសកម្ពុជា",
        char_count=21,
        language="km-KH",
        output_format=AudioFormat.MP3,
    )

    created = await repo.create(job)
    assert created.status == JobStatus.QUEUED

    # Update status to PROCESSING
    in_progress = await repo.update_status(
        job_id="job-uuid-100",
        status=JobStatus.PROCESSING,
    )
    assert in_progress.status == JobStatus.PROCESSING

    # Complete job with output artifact
    completed = await repo.update_status(
        job_id="job-uuid-100",
        status=JobStatus.COMPLETED,
        output_audio_key="audio/jobs/job-uuid-100.mp3",
        duration_seconds=3.45,
    )
    assert completed.status == JobStatus.COMPLETED
    assert completed.output_audio_key == "audio/jobs/job-uuid-100.mp3"
    assert completed.audio_duration_seconds == 3.45


@pytest.mark.asyncio
async def test_usage_repository(async_session: AsyncSession) -> None:
    """Test UsageRepository recording and monthly sum aggregation."""
    repo = SqlUsageRepository(async_session)

    now = datetime.utcnow()
    record1 = UsageRecord(
        id="usage-1",
        api_key_id="key-1",
        owner_id="dev_user",
        job_id="job-1",
        operation="tts_synthesis",
        characters_processed=500,
        duration_seconds=5.0,
        timestamp=now,
    )
    record2 = UsageRecord(
        id="usage-2",
        api_key_id="key-1",
        owner_id="dev_user",
        job_id="job-2",
        operation="tts_synthesis",
        characters_processed=750,
        duration_seconds=7.5,
        timestamp=now,
    )

    await repo.record_usage(record1)
    await repo.record_usage(record2)

    total = await repo.get_monthly_usage("dev_user", now.year, now.month)
    assert total == 1250


@pytest.mark.asyncio
async def test_local_storage_adapter(tmp_path: Path) -> None:
    """Test LocalStorageAdapter file upload, download, URL resolution, and deletion."""
    storage = LocalStorageAdapter(base_directory=str(tmp_path / "test_storage"))

    test_bytes = b"ID3v2-fake-mp3-audio-payload-for-testing"
    file_key = "voices/previews/sample_1.mp3"

    # Upload
    uploaded_key = await storage.upload(file_key, test_bytes, content_type="audio/mpeg")
    assert uploaded_key == file_key

    # Download
    downloaded_bytes = await storage.download(file_key)
    assert downloaded_bytes == test_bytes

    # URL
    url = await storage.get_download_url(file_key)
    assert url == f"/api/v1/storage/{file_key}"

    # Delete
    deleted = await storage.delete(file_key)
    assert deleted is True

    # Delete non-existent file returns False
    assert await storage.delete("non_existent.mp3") is False
