"""SQLAlchemy model for speech synthesis and processing jobs."""

from typing import Any

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vocara.domain.enums import AudioFormat, JobStatus, JobType
from vocara.infrastructure.db.base import Base, IdMixin, TimestampMixin


class JobModel(Base, IdMixin, TimestampMixin):
    """Database model tracking job lifecycle and generated artifacts."""

    __tablename__ = "jobs"

    job_type: Mapped[str] = mapped_column(
        String(30), default=JobType.TTS_BATCH.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.QUEUED.value, index=True, nullable=False
    )
    owner_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    voice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="km-KH", nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    output_format: Mapped[str] = mapped_column(
        String(10), default=AudioFormat.MP3.value, nullable=False
    )
    output_audio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
