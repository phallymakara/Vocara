"""Usage metering and quota management service."""

import uuid
from datetime import datetime
from typing import Any

from vocara.core.exceptions import QuotaExceededError
from vocara.domain.entities import ApiKey, UsageRecord
from vocara.domain.enums import ApiKeyStatus
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
        self,
        owner_id: str,
        year: int | None = None,
        month: int | None = None,
        tz_offset_minutes: int = 0,
    ) -> dict[str, Any]:
        """Aggregate monthly character consumption against developer quotas."""
        now = datetime.utcnow()
        target_year = year or now.year
        target_month = month or now.month

        used_chars = await self.usage_repo.get_monthly_usage(
            owner_id=owner_id, year=target_year, month=target_month
        )
        analytics = await self.usage_repo.get_monthly_analytics(
            owner_id=owner_id,
            year=target_year,
            month=target_month,
            tz_offset_minutes=tz_offset_minutes,
        )

        keys = await self.api_key_repo.list_by_owner(owner_id)
        active_keys = [k for k in keys if k.status == ApiKeyStatus.ACTIVE]
        quota_keys = active_keys if active_keys else keys
        total_quota = sum(k.char_quota_per_month for k in quota_keys) if quota_keys else 100000
        remaining = max(0, total_quota - used_chars)
        percent = round((used_chars / total_quota * 100), 2) if total_quota > 0 else 0.0

        by_key_stats = analytics.get("by_key", {})
        by_api_key = []
        for k in keys:
            stat = by_key_stats.get(k.id, {})
            by_api_key.append(
                {
                    "api_key_id": k.id,
                    "name": k.name,
                    "key_prefix": k.key_prefix,
                    "status": k.status.value,
                    "rate_limit_per_minute": k.rate_limit_per_minute,
                    "char_quota_per_month": k.char_quota_per_month,
                    "requests": int(stat.get("requests", 0)),
                    "characters": int(stat.get("characters", 0)),
                    "duration_seconds": float(stat.get("duration_seconds", 0.0)),
                }
            )
        by_api_key.sort(key=lambda item: (item["characters"], item["requests"]), reverse=True)

        return {
            "owner_id": owner_id,
            "year": target_year,
            "month": target_month,
            "characters_used": used_chars,
            "total_quota": total_quota,
            "quota_remaining": remaining,
            "quota_percentage_used": percent,
            "total_requests": analytics.get("total_requests", 0),
            "total_audio_seconds": analytics.get("total_audio_seconds", 0.0),
            "daily_usage": analytics.get("daily_usage", []),
            "by_operation": analytics.get("by_operation", []),
            "monthly_usage": analytics.get("monthly_usage", []),
            "hourly_usage": analytics.get("hourly_usage", []),
            "hourly_by_date": analytics.get("hourly_by_date", {}),
            "by_api_key": by_api_key,
        }
