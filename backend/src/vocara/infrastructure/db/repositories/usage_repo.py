"""SQLAlchemy repository implementation for UsageRepository port."""

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import UsageRecord
from vocara.domain.ports import UsageRepository
from vocara.infrastructure.db.models.usage import UsageRecordModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlUsageRepository(BaseRepository[UsageRecordModel], UsageRepository):
    """Repository adapter for usage and metering audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UsageRecordModel, session)

    async def record_usage(self, record: UsageRecord) -> None:
        """Persist a single usage event."""
        model = UsageRecordModel(
            id=record.id,
            api_key_id=record.api_key_id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            operation=record.operation,
            characters_processed=record.characters_processed,
            duration_seconds=record.duration_seconds,
            timestamp=record.timestamp,
        )
        await self._create_model(model)

    async def get_monthly_usage(self, owner_id: str, year: int, month: int) -> int:
        """Calculate total characters processed for a specific calendar month."""
        query = select(func.coalesce(func.sum(UsageRecordModel.characters_processed), 0)).where(
            UsageRecordModel.owner_id == owner_id,
            extract("year", UsageRecordModel.timestamp) == year,
            extract("month", UsageRecordModel.timestamp) == month,
        )
        result = await self.session.execute(query)
        total = result.scalar_one_or_none()
        return int(total) if total else 0
