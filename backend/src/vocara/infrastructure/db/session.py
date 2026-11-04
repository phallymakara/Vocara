"""Database session management and async engine configuration."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vocara.core.config import Settings, get_settings


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create async SQLAlchemy engine from application settings."""
    cfg = settings or get_settings()
    url_str = str(cfg.DATABASE_URL)
    kwargs: dict[str, object] = {
        "echo": cfg.DB_ECHO,
        "future": True,
    }
    if not url_str.startswith("sqlite"):
        kwargs["pool_size"] = cfg.DB_POOL_SIZE
        kwargs["max_overflow"] = cfg.DB_MAX_OVERFLOW
    return create_async_engine(cfg.DATABASE_URL, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessionmaker configured for async context."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper yielding an active async database session."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
