"""SQLAlchemy repository implementation for WebhookRepository port."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import WebhookSubscription
from vocara.domain.ports import WebhookRepository
from vocara.infrastructure.db.models.webhook import WebhookModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlWebhookRepository(BaseRepository[WebhookModel], WebhookRepository):
    """Repository adapter for developer webhooks."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WebhookModel, session)

    def _to_entity(self, model: WebhookModel) -> WebhookSubscription:
        """Map ORM model to domain entity."""
        return WebhookSubscription(
            id=model.id,
            owner_id=model.owner_id,
            url=model.url,
            secret=model.secret,
            event_types=model.event_types or [],
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def _to_model(self, entity: WebhookSubscription) -> WebhookModel:
        """Map domain entity to ORM model."""
        return WebhookModel(
            id=entity.id,
            owner_id=entity.owner_id,
            url=entity.url,
            secret=entity.secret,
            event_types=entity.event_types,
            is_active=entity.is_active,
            created_at=entity.created_at,
        )

    async def get_by_id(self, subscription_id: str) -> WebhookSubscription | None:
        """Fetch a specific webhook subscription by its unique ID."""
        model = await self._get_model_by_id(subscription_id)
        if not model or not model.is_active:
            return None
        return self._to_entity(model)

    async def get_by_owner(self, owner_id: str) -> list[WebhookSubscription]:
        """Fetch all active webhook registrations for an account."""
        query = select(WebhookModel).where(
            WebhookModel.owner_id == owner_id,
            WebhookModel.is_active.is_(True),
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Register a new webhook subscription."""
        model = self._to_model(subscription)
        created_model = await self._create_model(model)
        return self._to_entity(created_model)

    async def delete(self, subscription_id: str) -> bool:
        """Remove a webhook subscription."""
        return await self._delete_model(subscription_id)
