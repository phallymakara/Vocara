"""DTO schemas for Webhook subscription management."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateWebhookRequest(BaseModel):
    """Payload to register a new webhook subscription callback."""

    url: str = Field(
        ...,
        max_length=500,
        description="Publicly accessible HTTP or HTTPS callback URL.",
    )
    event_types: list[str] = Field(
        default_factory=lambda: ["job.completed", "job.failed"],
        description=(
            "List of subscribed event names (e.g. ['job.completed', 'job.failed'] or ['*'])."
        ),
    )


class WebhookResponse(BaseModel):
    """Webhook registration metadata and signing secret."""

    id: str
    url: str
    event_types: list[str]
    secret: str = Field(
        description="HMAC-SHA256 signing secret for verifying callback authenticity."
    )
    is_active: bool
    created_at: datetime
