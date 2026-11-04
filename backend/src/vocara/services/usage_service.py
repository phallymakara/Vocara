"""Usage metering and quota management service."""

import uuid
from datetime import datetime
from typing import Any

from vocara.core.exceptions import QuotaExceededError
from vocara.domain.entities import ApiKey, UsageRecord
from vocara.domain.ports import ApiKeyRepository, UsageRepository


class UsageService:
    """Manages character quota enforcement and metering records."""

    def __init__(
        self,
        usage_repo: UsageRepository,
        api_key_repo: ApiKeyRepository,
    ) -> None:
        self.usage_repo = usage_repo
        self.api_key_repo = api_key_repo

    def check_quota(self, api_key: ApiKey, chars_needed: int) -> None:
        """Validate if API key has sufficient remaining monthly quota.

        Raises:
            QuotaExceededError: When requested characters would exceed allocated quota.
        """
        if not api_key.has_quota(chars_needed):
            raise QuotaExceededError(
                current_usage=api_key.chars_used_this_month,
                quota=api_key.char_quota_per_month,
            )

    async def record_usage(
        self,
        api_key: ApiKey,
        operation: str,
        characters: int,
        duration_seconds: float = 0.0,
        job_id: str | None = None,
    ) -> None:
        """Persist usage record and increment atomic counter on the key."""
        record = UsageRecord(
            id=str(uuid.uuid4()),
            api_key_id=api_key.id,
            owner_id=api_key.owner_id,
            job_id=job_id,
            operation=operation,
            characters_processed=characters,
            duration_seconds=duration_seconds,
            timestamp=datetime.utcnow(),
        )

        await self.usage_repo.record_usage(record)
        await self.api_key_repo.increment_usage(api_key.id, characters)

    async def get_usage_summary(
        self, owner_id: str, year: int | None = None, month: int | None = None
    ) -> dict[str, Any]:
        """Aggregate monthly character consumption against developer quotas."""
        now = datetime.utcnow()
        target_year = year or now.year
        target_month = month or now.month

        used_chars = await self.usage_repo.get_monthly_usage(
            owner_id=owner_id, year=target_year, month=target_month
        )

        keys = await self.api_key_repo.list_by_owner(owner_id)
        total_quota = sum(k.char_quota_per_month for k in keys) if keys else 100000
        remaining = max(0, total_quota - used_chars)
        percent = round((used_chars / total_quota * 100), 2) if total_quota > 0 else 0.0

        return {
            "owner_id": owner_id,
            "year": target_year,
            "month": target_month,
            "characters_used": used_chars,
            "total_quota": total_quota,
            "quota_remaining": remaining,
            "quota_percentage_used": percent,
        }
