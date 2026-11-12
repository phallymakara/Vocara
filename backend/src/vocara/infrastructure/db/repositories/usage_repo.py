"""SQLAlchemy repository implementation for UsageRepository port."""

from datetime import date, timedelta
from typing import Any

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

    async def get_monthly_analytics(
        self, owner_id: str, year: int, month: int, tz_offset_minutes: int = 0
    ) -> dict[str, Any]:
        """Aggregate monthly requests, duration, daily series, and operation breakdown."""
        base_filter = (
            UsageRecordModel.owner_id == owner_id,
            extract("year", UsageRecordModel.timestamp) == year,
            extract("month", UsageRecordModel.timestamp) == month,
        )

        # Totals
        totals_q = select(
            func.count(UsageRecordModel.id),
            func.coalesce(func.sum(UsageRecordModel.duration_seconds), 0.0),
        ).where(*base_filter)
        totals_row = (await self.session.execute(totals_q)).one()
        total_requests = int(totals_row[0] or 0)
        total_audio_seconds = round(float(totals_row[1] or 0.0), 2)

        # Daily series & per-key breakdown (grouped in Python from matching month rows for SQLite/Postgres parity)
        records_q = (
            select(
                UsageRecordModel.timestamp,
                UsageRecordModel.operation,
                UsageRecordModel.api_key_id,
                UsageRecordModel.characters_processed,
                UsageRecordModel.duration_seconds,
            )
            .where(*base_filter)
            .order_by(UsageRecordModel.timestamp.asc())
        )
        rows = (await self.session.execute(records_q)).all()

        daily_map: dict[str, dict[str, Any]] = {}
        op_map: dict[str, dict[str, Any]] = {}
        key_map: dict[str, dict[str, Any]] = {}
        hourly_map: dict[int, dict[str, Any]] = {
            h: {"hour": h, "characters": 0, "requests": 0, "duration_seconds": 0.0}
            for h in range(24)
        }
        hourly_by_date_map: dict[str, dict[int, dict[str, Any]]] = {}
        offset_delta = timedelta(minutes=tz_offset_minutes)

        for ts, op, key_id, chars, dur in rows:
            local_ts = ts + offset_delta if hasattr(ts, "hour") else ts
            day_key = local_ts.date().isoformat() if hasattr(local_ts, "date") else date.today().isoformat()
            day_entry = daily_map.setdefault(
                day_key,
                {"date": day_key, "characters": 0, "requests": 0, "duration_seconds": 0.0},
            )
            day_entry["characters"] += int(chars or 0)
            day_entry["requests"] += 1
            day_entry["duration_seconds"] = round(
                day_entry["duration_seconds"] + float(dur or 0.0), 2
            )

            if hasattr(local_ts, "hour"):
                h_entry = hourly_map[local_ts.hour]
                h_entry["characters"] += int(chars or 0)
                h_entry["requests"] += 1
                h_entry["duration_seconds"] = round(
                    h_entry["duration_seconds"] + float(dur or 0.0), 2
                )

                day_hours = hourly_by_date_map.setdefault(day_key, {})
                dh_entry = day_hours.setdefault(
                    local_ts.hour,
                    {"hour": local_ts.hour, "characters": 0, "requests": 0, "duration_seconds": 0.0},
                )
                dh_entry["characters"] += int(chars or 0)
                dh_entry["requests"] += 1
                dh_entry["duration_seconds"] = round(
                    dh_entry["duration_seconds"] + float(dur or 0.0), 2
                )

            op_key = str(op or "unknown")
            op_entry = op_map.setdefault(
                op_key,
                {"operation": op_key, "requests": 0, "characters": 0, "duration_seconds": 0.0},
            )
            op_entry["requests"] += 1
            op_entry["characters"] += int(chars or 0)
            op_entry["duration_seconds"] = round(
                op_entry["duration_seconds"] + float(dur or 0.0), 2
            )

            if key_id:
                k_entry = key_map.setdefault(
                    str(key_id),
                    {"api_key_id": str(key_id), "requests": 0, "characters": 0, "duration_seconds": 0.0},
                )
                k_entry["requests"] += 1
                k_entry["characters"] += int(chars or 0)
                k_entry["duration_seconds"] = round(
                    k_entry["duration_seconds"] + float(dur or 0.0), 2
                )

        # Monthly breakdown across the target calendar year (months 1..12)
        year_q = select(
            UsageRecordModel.timestamp,
            UsageRecordModel.characters_processed,
            UsageRecordModel.duration_seconds,
        ).where(
            UsageRecordModel.owner_id == owner_id,
            extract("year", UsageRecordModel.timestamp) == year,
        )
        year_rows = (await self.session.execute(year_q)).all()
        monthly_map: dict[int, dict[str, Any]] = {
            m: {"month": m, "characters": 0, "requests": 0, "duration_seconds": 0.0}
            for m in range(1, 13)
        }
        for ts, chars, dur in year_rows:
            m_num = ts.month if hasattr(ts, "month") else month
            if m_num in monthly_map:
                monthly_map[m_num]["characters"] += int(chars or 0)
                monthly_map[m_num]["requests"] += 1
                monthly_map[m_num]["duration_seconds"] = round(
                    monthly_map[m_num]["duration_seconds"] + float(dur or 0.0), 2
                )

        daily_usage = [daily_map[k] for k in sorted(daily_map.keys())]
        by_operation = sorted(op_map.values(), key=lambda x: x["characters"], reverse=True)
        monthly_usage = [monthly_map[m] for m in range(1, 13)]
        hourly_usage = [hourly_map[h] for h in range(24)]
        hourly_by_date = {
            day_k: [hours_dict[h] for h in sorted(hours_dict.keys())]
            for day_k, hours_dict in hourly_by_date_map.items()
        }

        return {
            "total_requests": total_requests,
            "total_audio_seconds": total_audio_seconds,
            "daily_usage": daily_usage,
            "by_operation": by_operation,
            "monthly_usage": monthly_usage,
            "hourly_usage": hourly_usage,
            "hourly_by_date": hourly_by_date,
            "by_key": key_map,
        }
