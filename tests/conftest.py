"""Pytest fixtures and test environment configuration."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import all models to ensure metadata is populated
import vocara.infrastructure.db.models  # noqa: F401
from vocara.core.config import Settings
from vocara.infrastructure.db.base import Base
from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine
from vocara.infrastructure.queue.redis_queue import RedisJobQueue
from vocara.infrastructure.storage.local import LocalStorageAdapter
from vocara.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated in-memory/test settings."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        STORAGE_BACKEND="local",
        LOCAL_STORAGE_DIR="./test_storage",
        INFERENCE_ENGINE_TYPE="fake",
    )


@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide isolated in-memory SQLite async engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an active async database session for repository tests."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Provide session factory bound to test async engine."""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
def test_app(test_settings: Settings):
    """Create test FastAPI application instance."""
    return create_app(test_settings)


@pytest.fixture
async def async_client(test_app, async_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP async client bound to test_app with configured DB session factory."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    test_app.state.container.db_engine = async_engine
    test_app.state.container.session_factory = session_factory
    test_app.state.container.storage = LocalStorageAdapter(
        test_app.state.settings.LOCAL_STORAGE_DIR
    )
    test_app.state.container.job_queue = RedisJobQueue(None)
    test_app.state.container.inference_engine = FakeInferenceEngine()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
