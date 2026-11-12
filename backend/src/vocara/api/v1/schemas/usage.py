"""DTO schemas for usage metering and quota tracking."""

from pydantic import BaseModel, Field


class DailyUsagePoint(BaseModel):
    """Single day usage aggregation."""

    date: str
    characters: int
    requests: int
    duration_seconds: float


class OperationUsagePoint(BaseModel):
    """Per-operation usage aggregation."""

    operation: str
    requests: int
    characters: int
    duration_seconds: float


class MonthlyUsagePoint(BaseModel):
    """Single month usage aggregation within a year."""

    month: int
    characters: int
    requests: int
    duration_seconds: float


class HourlyUsagePoint(BaseModel):
    """Single hour-of-day (0-23) usage aggregation."""

    hour: int
    characters: int
    requests: int
    duration_seconds: float


class ApiKeyUsagePoint(BaseModel):
    """Per-API-key usage and quota attribution for the billing period."""

    api_key_id: str
    name: str
    key_prefix: str
    status: str
    rate_limit_per_minute: int
    char_quota_per_month: int
    requests: int
    characters: int
    duration_seconds: float


class UsageSummaryResponse(BaseModel):
    """Monthly usage metrics and analytics for developer account."""

    owner_id: str
    year: int
    month: int
    characters_used: int = Field(..., description="Characters consumed in specified month")
    total_quota: int = Field(..., description="Total combined monthly character allowance")
    quota_remaining: int = Field(..., description="Remaining character quota for the month")
    quota_percentage_used: float = Field(..., description="Percentage of quota consumed")
    total_requests: int = Field(default=0, description="Total API synthesis/voice requests in period")
    total_audio_seconds: float = Field(default=0.0, description="Total audio duration synthesized in seconds")
    daily_usage: list[DailyUsagePoint] = Field(default_factory=list, description="Daily character & request series")
    by_operation: list[OperationUsagePoint] = Field(default_factory=list, description="Breakdown by API operation")
    monthly_usage: list[MonthlyUsagePoint] = Field(default_factory=list, description="Per-month usage across calendar year")
    hourly_usage: list[HourlyUsagePoint] = Field(default_factory=list, description="Hourly (0-23) usage distribution")
    hourly_by_date: dict[str, list[HourlyUsagePoint]] = Field(
        default_factory=dict, description="Hourly usage points keyed by YYYY-MM-DD"
    )
    by_api_key: list[ApiKeyUsagePoint] = Field(default_factory=list, description="Per-API-key usage breakdown")
