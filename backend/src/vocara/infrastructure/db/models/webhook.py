"""SQLAlchemy model for developer webhook subscriptions."""

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from vocara.infrastructure.db.base import Base, IdMixin, TimestampMixin


class WebhookModel(Base, IdMixin, TimestampMixin):
    """Database model for developer webhook endpoint subscriptions."""

    __tablename__ = "webhooks"

    owner_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
