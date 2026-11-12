"""SQLAlchemy repository implementation for ApiKeyRepository port."""

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import ApiKey
from vocara.domain.enums import ApiKeyStatus
from vocara.domain.ports import ApiKeyRepository
from vocara.infrastructure.db.models.api_key import ApiKeyModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlApiKeyRepository(BaseRepository[ApiKeyModel], ApiKeyRepository):
    """Repository adapter implementing ApiKeyRepository against PostgreSQL/SQLite."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ApiKeyModel, session)

    def _to_entity(self, model: ApiKeyModel) -> ApiKey:
        """Map ORM model to pure domain entity."""
        return ApiKey(
            id=model.id,
            key_prefix=model.key_prefix,
            hashed_secret=model.hashed_secret,
            owner_id=model.owner_id,
            name=model.name,
            status=ApiKeyStatus(model.status),
            rate_limit_per_minute=model.rate_limit_per_minute,
            char_quota_per_month=model.char_quota_per_month,
            chars_used_this_month=model.chars_used_this_month,
            last_used_at=model.last_used_at,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )

    def _to_model(self, entity: ApiKey) -> ApiKeyModel:
        """Map domain entity to ORM model."""
        return ApiKeyModel(
            id=entity.id,
            key_prefix=entity.key_prefix,
            hashed_secret=entity.hashed_secret,
            owner_id=entity.owner_id,
            name=entity.name,
            status=entity.status.value,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            char_quota_per_month=entity.char_quota_per_month,
            chars_used_this_month=entity.chars_used_this_month,
            last_used_at=entity.last_used_at,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
        )

    async def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        """Indexed prefix lookup to authenticate API requests."""
        query = select(ApiKeyModel).where(
            ApiKeyModel.key_prefix == key_prefix,
            ApiKeyModel.status == ApiKeyStatus.ACTIVE.value,
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        """Lookup API key by UUID."""
        model = await self._get_model_by_id(key_id)
        return self._to_entity(model) if model else None

    async def list_by_owner(self, owner_id: str) -> list[ApiKey]:
        """List active and revoked keys for a specific developer account."""
        query = select(ApiKeyModel).where(ApiKeyModel.owner_id == owner_id)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist a new API key."""
        model = self._to_model(api_key)
        created_model = await self._create_model(model)
        return self._to_entity(created_model)

    async def update_name(self, key_id: str, name: str) -> ApiKey | None:
        """Update the label of an existing API key."""
        model = await self._get_model_by_id(key_id)
        if not model:
            return None
        model.name = name
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def revoke(self, key_id: str) -> bool:
        """Revoke an API key immediately."""
        query = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(status=ApiKeyStatus.REVOKED.value)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return True

    async def delete(self, key_id: str) -> bool:
        """Permanently delete an API key record."""
        query = delete(ApiKeyModel).where(ApiKeyModel.id == key_id)
        result = await self.session.execute(query)
        await self.session.flush()
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return True

    async def increment_usage(self, key_id: str, characters: int) -> None:
        """Atomically increment character usage counter."""
        query = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(chars_used_this_month=ApiKeyModel.chars_used_this_month + characters)
        )
        await self.session.execute(query)
        await self.session.flush()
