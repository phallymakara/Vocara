"""DTO schemas for asynchronous job tracking and inspection."""

from datetime import datetime

from pydantic import BaseModel, Field

from vocara.domain.enums import JobStatus, JobType


class JobResponse(BaseModel):
    """Job tracking and metadata representation."""

    id: str
    job_type: JobType
    status: JobStatus
    owner_id: str
    voice_id: str | None = None
    char_count: int = Field(default=0, description="Number of text characters processed.")
    language: str
    output_format: str
    audio_duration_seconds: float = Field(default=0.0, description="Duration in seconds.")
    error_message: str | None = None
    result_url: str | None = Field(
        default=None, description="URL endpoint to download synthesized audio when completed."
    )
    created_at: datetime
    updated_at: datetime
