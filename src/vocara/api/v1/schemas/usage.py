"""DTO schemas for usage metering and quota tracking."""

from pydantic import BaseModel, Field


class UsageSummaryResponse(BaseModel):
    """Monthly usage metrics for developer account."""

    owner_id: str
    year: int
    month: int
    characters_used: int = Field(..., description="Characters consumed in specified month")
    total_quota: int = Field(..., description="Total combined monthly character allowance")
    quota_remaining: int = Field(..., description="Remaining character quota for the month")
    quota_percentage_used: float = Field(..., description="Percentage of quota consumed")
