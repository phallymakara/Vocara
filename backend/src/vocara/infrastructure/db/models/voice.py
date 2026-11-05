"""SQLAlchemy model for voices."""

from typing import Any

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.infrastructure.db.base import Base, IdMixin, TimestampMixin


class VoiceModel(Base, IdMixin, TimestampMixin):
    """Database model for voice profiles (built-in, cloned, or designed)."""

    __tablename__ = "voices"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_type: Mapped[str] = mapped_column(
        String(20), default=VoiceType.CLONED.value, nullable=False
    )
    owner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="km-KH", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_audio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_audio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modifiers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), default=VoiceVisibility.PRIVATE.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
