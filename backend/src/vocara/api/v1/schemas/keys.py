"""DTO schemas for developer API keys."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    """Request payload for creating a new developer API key."""

    name: str = Field(..., min_length=2, max_length=100, description="Label for the API key")
    is_live: bool = Field(default=True, description="True for live key, False for test key")
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=1000, description="Rate limit allowance in requests per minute"
    )
    char_quota_per_month: int = Field(
        default=100000, ge=1000, le=10000000, description="Monthly character generation quota"
    )


class ApiKeyResponse(BaseModel):
    """Public metadata for an API key (raw secret is excluded)."""

    id: str
    name: str
    key_prefix: str
    status: str
    rate_limit_per_minute: int
    char_quota_per_month: int
    chars_used_this_month: int
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response returned upon API key creation containing the raw secret exactly once."""

    api_key: str = Field(
        ...,
        description="The secret API key. Store this securely as it will not be displayed again.",
    )
