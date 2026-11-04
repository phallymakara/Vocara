"""SQLAlchemy model for API keys and developer access."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from vocara.domain.enums import ApiKeyStatus
from vocara.infrastructure.db.base import Base, IdMixin, TimestampMixin


class ApiKeyModel(Base, IdMixin, TimestampMixin):
    """Database model storing developer API keys, hashed secrets, and quotas."""

    __tablename__ = "api_keys"

    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    hashed_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ApiKeyStatus.ACTIVE.value, nullable=False
    )
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    char_quota_per_month: Mapped[int] = mapped_column(Integer, default=100000, nullable=False)
    chars_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
