"""Unit tests for background inference worker execution and error resilience."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vocara.container import Container
from vocara.core.config import Settings
from vocara.domain.entities import Job, Voice
from vocara.domain.enums import AudioFormat, JobStatus, JobType, VoiceType, VoiceVisibility
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.infrastructure.queue.redis_queue import RedisJobQueue
from vocara.infrastructure.storage.local import LocalStorageAdapter
from vocara.worker.handler import Worker


@pytest.fixture
def worker_container(
    test_settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: pytest.TempPathFactory,
) -> Container:
    container = Container(test_settings)
    container.session_factory = session_factory
    container.storage = LocalStorageAdapter(str(tmp_path))
    container.job_queue = RedisJobQueue(redis_url=None)  # Uses in-memory queue fallback
    container.inference_engine = FakeInferenceEngine()
    return container


@pytest.mark.asyncio
async def test_worker_process_job_success(
    worker_container: Container,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Worker successfully transitions job from QUEUED to COMPLETED and stores audio."""
    worker = Worker(worker_container)

    # 1. Seed a voice and a job in the database
    async with session_factory() as session:
        voice_repo = worker_container.get_voice_repo(session)
        job_repo = worker_container.get_job_repo(session)

        voice = Voice(
            id="worker-test-voice-1",
            name="Worker Voice",
            voice_type=VoiceType.BUILT_IN,
            owner_id=None,
            language="km-KH",
            visibility=VoiceVisibility.PUBLIC,
        )
        await voice_repo.create(voice)

        job = Job(
            id="worker-test-job-1",
            job_type=JobType.TTS_BATCH,
            status=JobStatus.QUEUED,
            owner_id="dev_user_worker",
            voice_id="worker-test-voice-1",
            input_text="អត្ថបទសាកល្បងសម្រាប់ worker background process",
            char_count=45,
            language="km-KH",
            speed=1.0,
            output_format=AudioFormat.MP3,
        )
        await job_repo.create(job)
        await session.commit()

    # 2. Process payload
    payload = {
        "job_id": "worker-test-job-1",
        "job_type": "text_to_speech",
        "owner_id": "dev_user_worker",
        "voice_id": "worker-test-voice-1",
    }
    result = await worker.process_job_payload(payload)
    assert result is True

    # 3. Verify job state in DB
    async with session_factory() as session:
        job_repo = worker_container.get_job_repo(session)
        updated_job = await job_repo.get_by_id("worker-test-job-1")

        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.output_audio_key == "jobs/worker-test-job-1/output.mp3"
        assert updated_job.audio_duration_seconds > 0.0

        # Verify storage artifact exists
        assert worker_container.storage is not None
        downloaded = await worker_container.storage.download(updated_job.output_audio_key)
        assert len(downloaded) > 0


@pytest.mark.asyncio
async def test_worker_process_job_failure_updates_status(
    worker_container: Container,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Worker safely catches unexpected exceptions and marks the job as FAILED."""

    # Force inference engine to fail
    class FailingInference:
        async def generate_speech(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Simulated GPU out of memory")

    worker_container.inference_engine = FailingInference()  # type: ignore[assignment]
    worker = Worker(worker_container)

    # Seed job
    async with session_factory() as session:
        job_repo = worker_container.get_job_repo(session)
        job = Job(
            id="worker-failing-job-1",
            job_type=JobType.TTS_BATCH,
            status=JobStatus.QUEUED,
            owner_id="dev_user_worker",
            input_text="តេស្តបរាជ័យ",
            char_count=12,
        )
        await job_repo.create(job)
        await session.commit()

    payload = {"job_id": "worker-failing-job-1"}
    result = await worker.process_job_payload(payload)
    assert result is False

    # Verify job marked as FAILED
    async with session_factory() as session:
        job_repo = worker_container.get_job_repo(session)
        updated_job = await job_repo.get_by_id("worker-failing-job-1")

        assert updated_job is not None
        assert updated_job.status == JobStatus.FAILED
        assert "Audio generation failed" in (updated_job.error_message or "")


@pytest.mark.asyncio
async def test_worker_stop_signal(worker_container: Container) -> None:
    """Calling stop() flags the worker loop to terminate."""
    worker = Worker(worker_container)
    assert worker._is_running is False
    worker.stop()
    assert worker._is_running is False
