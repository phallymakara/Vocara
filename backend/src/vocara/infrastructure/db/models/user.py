"""SQLAlchemy model for authenticated platform users."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from vocara.infrastructure.db.base import Base, IdMixin, TimestampMixin


class UserModel(Base, IdMixin, TimestampMixin):
    """Database model storing developer/user accounts and login credentials."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

