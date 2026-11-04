"""API endpoints for developer usage metering and quotas."""

from fastapi import APIRouter, Query

from vocara.api.deps import CurrentApiKey, UsageServiceDep
from vocara.api.v1.schemas.usage import UsageSummaryResponse

router = APIRouter(prefix="/usage", tags=["Account & Keys"])


@router.get(
    "",
    response_model=UsageSummaryResponse,
    summary="Get Usage and Quota Summary",
)
async def get_usage(
    current_key: CurrentApiKey,
    usage_service: UsageServiceDep,
    year: int | None = Query(default=None, ge=2024, le=2050, description="Calendar year"),
    month: int | None = Query(default=None, ge=1, le=12, description="Calendar month (1-12)"),
) -> UsageSummaryResponse:
    """Retrieve monthly character consumption, allocated quota, and percentage used."""
    summary = await usage_service.get_usage_summary(
        owner_id=current_key.owner_id,
        year=year,
        month=month,
    )
    return UsageSummaryResponse(**summary)
