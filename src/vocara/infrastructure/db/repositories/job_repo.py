"""SQLAlchemy repository implementation for JobRepository port."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.core.exceptions import JobNotFoundError
from vocara.domain.entities import Job
from vocara.domain.enums import AudioFormat, JobStatus, JobType
from vocara.domain.ports import JobRepository
from vocara.infrastructure.db.models.job import JobModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlJobRepository(BaseRepository[JobModel], JobRepository):
    """Repository adapter implementing JobRepository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(JobModel, session)

    def _to_entity(self, model: JobModel) -> Job:
        """Map ORM model to domain entity."""
        return Job(
            id=model.id,
            job_type=JobType(model.job_type),
            status=JobStatus(model.status),
            owner_id=model.owner_id,
            voice_id=model.voice_id,
            input_text=model.input_text,
            char_count=model.char_count,
            language=model.language,
            speed=model.speed,
            output_format=AudioFormat(model.output_format),
            output_audio_key=model.output_audio_key,
            audio_duration_seconds=model.audio_duration_seconds,
            error_message=model.error_message,
            metadata=model.extra_metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Job) -> JobModel:
        """Map domain entity to ORM model."""
        return JobModel(
            id=entity.id,
            job_type=entity.job_type.value,
            status=entity.status.value,
            owner_id=entity.owner_id,
            voice_id=entity.voice_id,
            input_text=entity.input_text,
            char_count=entity.char_count,
            language=entity.language,
            speed=entity.speed,
            output_format=entity.output_format.value,
            output_audio_key=entity.output_audio_key,
            audio_duration_seconds=entity.audio_duration_seconds,
            error_message=entity.error_message,
            extra_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, job_id: str) -> Job | None:
        """Fetch job by ID."""
        model = await self._get_model_by_id(job_id)
        return self._to_entity(model) if model else None

    async def list_by_owner(self, owner_id: str, skip: int = 0, limit: int = 50) -> list[Job]:
        """Fetch jobs initiated by developer account."""
        query = (
            select(JobModel)
            .where(JobModel.owner_id == owner_id)
            .order_by(JobModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, job: Job) -> Job:
        """Persist new job."""
        model = self._to_model(job)
        created_model = await self._create_model(model)
        return self._to_entity(created_model)

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        output_audio_key: str | None = None,
        duration_seconds: float = 0.0,
        error_message: str | None = None,
    ) -> Job:
        """Update job lifecycle status, output key, duration, and error."""
        model = await self._get_model_by_id(job_id)
        if not model:
            raise JobNotFoundError(job_id)

        model.status = status.value if hasattr(status, "value") else str(status)
        if output_audio_key is not None:
            model.output_audio_key = output_audio_key
        if duration_seconds > 0:
            model.audio_duration_seconds = duration_seconds
        if error_message is not None:
            model.error_message = error_message

        updated = await self._update_model(model)
        return self._to_entity(updated)
