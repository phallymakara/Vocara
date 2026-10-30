"""Unit tests for WebhookService HMAC signing, delivery, and subscription isolation."""

import hashlib
import hmac
import json

import httpx
import pytest

from vocara.core.exceptions import EntityNotFoundError, VocaraError
from vocara.domain.entities import WebhookSubscription
from vocara.domain.ports import WebhookRepository
from vocara.services.webhook_service import WebhookService


class InMemoryWebhookRepo(WebhookRepository):
    """In-memory mock for WebhookRepository."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, WebhookSubscription] = {}

    async def get_by_id(self, subscription_id: str) -> WebhookSubscription | None:
        return self.subscriptions.get(subscription_id)

    async def get_by_owner(self, owner_id: str) -> list[WebhookSubscription]:
        return [s for s in self.subscriptions.values() if s.owner_id == owner_id and s.is_active]

    async def create(self, subscription: WebhookSubscription) -> WebhookSubscription:
        self.subscriptions[subscription.id] = subscription
        return subscription

    async def delete(self, subscription_id: str) -> bool:
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].is_active = False
            return True
        return False


@pytest.fixture
def webhook_repo() -> InMemoryWebhookRepo:
    return InMemoryWebhookRepo()


@pytest.fixture
def webhook_service(webhook_repo: InMemoryWebhookRepo) -> WebhookService:
    return WebhookService(webhook_repo=webhook_repo)


@pytest.mark.asyncio
async def test_create_webhook_success(webhook_service: WebhookService) -> None:
    """Creates a subscription with a valid whsec_ secret."""
    sub = await webhook_service.create_subscription(
        owner_id="dev_user_1",
        url="https://api.myapp.com/vocara-webhook",
        event_types=["job.completed"],
    )

    assert sub.id is not None
    assert sub.owner_id == "dev_user_1"
    assert sub.url == "https://api.myapp.com/vocara-webhook"
    assert sub.secret.startswith("whsec_")
    assert sub.event_types == ["job.completed"]


@pytest.mark.asyncio
async def test_create_webhook_invalid_url_fails(webhook_service: WebhookService) -> None:
    """Rejects URLs without http/https protocol."""
    with pytest.raises(VocaraError) as exc_info:
        await webhook_service.create_subscription(
            owner_id="dev_user_1",
            url="ftp://invalid-url.com",
        )

    assert exc_info.value.code == "INVALID_URL"


@pytest.mark.asyncio
async def test_delete_webhook_isolation(
    webhook_service: WebhookService, webhook_repo: InMemoryWebhookRepo
) -> None:
    """Cannot delete another user's webhook subscription."""
    sub = await webhook_service.create_subscription(
        owner_id="dev_user_1",
        url="https://myapp.com/webhook",
    )

    with pytest.raises(EntityNotFoundError):
        await webhook_service.delete_subscription(
            owner_id="other_user_2",
            subscription_id=sub.id,
        )


@pytest.mark.asyncio
async def test_dispatch_event_hmac_signature(
    webhook_service: WebhookService, webhook_repo: InMemoryWebhookRepo
) -> None:
    """Dispatches payload with correct HMAC-SHA256 signature in X-Vocara-Signature header."""
    received_requests: list[httpx.Request] = []

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        return httpx.Response(200, json={"status": "received"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    webhook_service._client = mock_client

    sub = await webhook_service.create_subscription(
        owner_id="dev_user_1",
        url="https://subscriber.example.com/webhook",
        event_types=["job.completed"],
    )

    event_data = {"job_id": "job_123", "status": "completed"}
    count = await webhook_service.dispatch_event(
        owner_id="dev_user_1",
        event_type="job.completed",
        data=event_data,
    )

    assert count == 1
    assert len(received_requests) == 1
    req = received_requests[0]

    # Verify signature
    sig_header = req.headers["X-Vocara-Signature"]
    assert sig_header.startswith("sha256=")
    expected_hex = hmac.new(sub.secret.encode("utf-8"), req.content, hashlib.sha256).hexdigest()
    assert sig_header == f"sha256={expected_hex}"

    # Verify body
    body = json.loads(req.content.decode("utf-8"))
    assert body["event"] == "job.completed"
    assert body["data"] == event_data


@pytest.mark.asyncio
async def test_dispatch_event_handles_network_failure(
    webhook_service: WebhookService,
) -> None:
    """Catches subscriber server errors without raising an exception."""

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    webhook_service._client = mock_client

    await webhook_service.create_subscription(
        owner_id="dev_user_1",
        url="https://broken-subscriber.local/webhook",
        event_types=["job.failed"],
    )

    count = await webhook_service.dispatch_event(
        owner_id="dev_user_1",
        event_type="job.failed",
        data={"error": "Something went wrong"},
    )
    assert count == 0
