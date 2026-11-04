"""Generic repository base providing reusable async CRUD operations."""

from typing import Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.infrastructure.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class encapsulating standard SQLAlchemy CRUD operations.

    Concrete domain repositories use these internal persistence helpers to implement
    pure domain repository ports without leaking ORM models or violating LSP.
    """

    def __init__(self, model_class: type[ModelType], session: AsyncSession) -> None:
        self.model_class = model_class
        self.session = session

    async def _get_model_by_id(self, entity_id: str) -> ModelType | None:
        """Fetch model by primary key."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def _list_all_models(self, skip: int = 0, limit: int = 50) -> list[ModelType]:
        """Fetch paginated models."""
        result = await self.session.execute(select(self.model_class).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def _create_model(self, instance: ModelType) -> ModelType:
        """Persist a new model instance."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def _update_model(self, instance: ModelType) -> ModelType:
        """Update and refresh existing model."""
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def _delete_model(self, entity_id: str) -> bool:
        """Delete an entity by primary key."""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == entity_id)  # type: ignore[attr-defined]
        )
        await self.session.flush()
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return True
