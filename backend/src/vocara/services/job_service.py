"""Job lifecycle and async background scheduling service."""

import uuid
from typing import Any

from vocara.core.exceptions import EntityNotFoundError, JobNotFoundError, VocaraError
from vocara.domain.entities import Job
from vocara.domain.enums import AudioFormat, JobStatus, JobType
from vocara.domain.ports import BlobStorage, JobQueue, JobRepository


class JobService:
    """Manages creation, status tracking, queue dispatching, and output artifacts for jobs."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_queue: JobQueue | None = None,
        storage: BlobStorage | None = None,
    ) -> None:
        self.job_repo = job_repo
        self.job_queue = job_queue
        self.storage = storage

    async def create_job(
        self,
        owner_id: str,
        job_type: JobType,
        voice_id: str | None = None,
        input_text: str | None = None,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """Create, persist, and dispatch a new asynchronous job."""
        job_id = str(uuid.uuid4())
        char_count = len(input_text) if input_text else 0

        job = Job(
            id=job_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            owner_id=owner_id,
            voice_id=voice_id,
            input_text=input_text,
            char_count=char_count,
            language=language,
            speed=speed,
            output_format=output_format,
            metadata=metadata or {},
        )

        persisted_job = await self.job_repo.create(job)

        # Dispatch task to background queue if configured
        if self.job_queue:
            payload = {
                "job_id": job_id,
                "job_type": job_type.value,
                "owner_id": owner_id,
                "voice_id": voice_id,
                "text": input_text,
                "language": language,
                "speed": speed,
                "output_format": output_format.value,
                "metadata": metadata or {},
            }
            await self.job_queue.enqueue("jobs:inference", payload)

        return persisted_job

    async def get_job(self, job_id: str, owner_id: str) -> Job:
        """Retrieve job status, enforcing tenant ownership."""
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.owner_id != owner_id:
            raise JobNotFoundError(job_id)
        return job

    async def list_jobs(self, owner_id: str, skip: int = 0, limit: int = 50) -> list[Job]:
        """List historical jobs for caller."""
        return await self.job_repo.list_by_owner(owner_id=owner_id, skip=skip, limit=limit)

    async def get_job_audio(self, job_id: str, owner_id: str) -> tuple[bytes, str]:
        """Download synthesized audio result for completed job."""
        job = await self.get_job(job_id, owner_id)

        if job.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
            raise VocaraError(
                f"Job '{job_id}' is still in progress (status: {job.status.value}).",
                code="JOB_IN_PROGRESS",
            )

        if job.status == JobStatus.FAILED:
            raise VocaraError(
                f"Job '{job_id}' failed: {job.error_message or 'Unknown error'}",
                code="JOB_FAILED",
            )

        if not job.output_audio_key:
            raise EntityNotFoundError(f"No audio output artifact recorded for job '{job_id}'.")

        if not self.storage:
            raise VocaraError("Storage backend is not configured.", code="STORAGE_UNAVAILABLE")

        audio_bytes = await self.storage.download(job.output_audio_key)
        media_type = (
            "audio/mpeg"
            if job.output_format == AudioFormat.MP3
            else f"audio/{job.output_format.value}"
        )
        return audio_bytes, media_type

    async def complete_job(
        self,
        job_id: str,
        output_audio_key: str,
        duration_seconds: float = 0.0,
    ) -> Job:
        """Mark job as completed with output artifact."""
        return await self.job_repo.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            output_audio_key=output_audio_key,
            duration_seconds=duration_seconds,
        )

    async def fail_job(self, job_id: str, error_message: str) -> Job:
        """Mark job as failed with reason."""
        return await self.job_repo.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_message=error_message,
        )
