"""API endpoints for Webhook subscription management."""

from fastapi import APIRouter, status

from vocara.api.deps import CurrentApiKey, WebhookServiceDep
from vocara.api.v1.schemas.webhook import CreateWebhookRequest, WebhookResponse
from vocara.domain.entities import WebhookSubscription

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _to_webhook_response(sub: WebhookSubscription) -> WebhookResponse:
    """Map domain entity to DTO."""
    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        event_types=sub.event_types,
        secret=sub.secret,
        is_active=sub.is_active,
        created_at=sub.created_at,
    )


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Webhook Subscription",
)
async def create_webhook(
    payload: CreateWebhookRequest,
    current_key: CurrentApiKey,
    webhook_service: WebhookServiceDep,
) -> WebhookResponse:
    """Register a new webhook URL to receive asynchronous events."""
    sub = await webhook_service.create_subscription(
        owner_id=current_key.owner_id,
        url=payload.url,
        event_types=payload.event_types,
    )
    return _to_webhook_response(sub)


@router.get(
    "",
    response_model=list[WebhookResponse],
    summary="List Webhook Subscriptions",
)
async def list_webhooks(
    current_key: CurrentApiKey,
    webhook_service: WebhookServiceDep,
) -> list[WebhookResponse]:
    """Retrieve all active webhook subscriptions for the authenticated account."""
    subs = await webhook_service.list_subscriptions(owner_id=current_key.owner_id)
    return [_to_webhook_response(s) for s in subs]


@router.delete(
    "/{subscription_id}",
    summary="Delete Webhook Subscription",
)
async def delete_webhook(
    subscription_id: str,
    current_key: CurrentApiKey,
    webhook_service: WebhookServiceDep,
) -> dict[str, str]:
    """Revoke and delete a registered webhook subscription."""
    await webhook_service.delete_subscription(
        owner_id=current_key.owner_id,
        subscription_id=subscription_id,
    )
    return {"status": "deleted", "subscription_id": subscription_id}
