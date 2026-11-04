"""Webhook subscription management and secure HMAC event delivery service."""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from vocara.core.exceptions import EntityNotFoundError, InvalidWebhookUrlError
from vocara.domain.entities import WebhookSubscription
from vocara.domain.ports import WebhookRepository

logger = structlog.get_logger("vocara.webhooks")


class WebhookService:
    """Manages developer webhooks and handles secure event notification delivery."""

    def __init__(
        self,
        webhook_repo: WebhookRepository,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.webhook_repo = webhook_repo
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def create_subscription(
        self,
        owner_id: str,
        url: str,
        event_types: list[str] | None = None,
    ) -> WebhookSubscription:
        """Register a new webhook callback URL with a unique signing secret."""
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            raise InvalidWebhookUrlError("Webhook URL must begin with 'http://' or 'https://'.")

        events = event_types or ["job.completed", "job.failed"]
        secret = f"whsec_{secrets.token_hex(24)}"
        subscription_id = str(uuid.uuid4())

        subscription = WebhookSubscription(
            id=subscription_id,
            owner_id=owner_id,
            url=clean_url,
            secret=secret,
            event_types=events,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return await self.webhook_repo.create(subscription)

    async def list_subscriptions(self, owner_id: str) -> list[WebhookSubscription]:
        """Fetch all active webhook registrations for an account."""
        return await self.webhook_repo.get_by_owner(owner_id)

    async def delete_subscription(self, owner_id: str, subscription_id: str) -> bool:
        """Revoke a webhook subscription, enforcing tenant isolation."""
        sub = await self.webhook_repo.get_by_id(subscription_id)
        if not sub or sub.owner_id != owner_id:
            raise EntityNotFoundError(f"Webhook '{subscription_id}' was not found.")

        return await self.webhook_repo.delete(subscription_id)

    async def dispatch_event(
        self,
        owner_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """Sign and dispatch an event payload to all matching active subscriber webhooks."""
        subscriptions = await self.webhook_repo.get_by_owner(owner_id)
        if not subscriptions:
            return 0

        matching = [
            s
            for s in subscriptions
            if s.is_active and (event_type in s.event_types or "*" in s.event_types)
        ]
        if not matching:
            return 0

        payload_obj = {
            "id": f"evt_{uuid.uuid4().hex[:16]}",
            "event": event_type,
            "created_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        payload_bytes = json.dumps(payload_obj).encode("utf-8")

        client = await self._get_client()
        successful_dispatches = 0

        for sub in matching:
            signature = hmac.new(
                sub.secret.encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "X-Vocara-Signature": f"sha256={signature}",
                "User-Agent": "Vocara-Webhook/1.0",
            }

            try:
                resp = await client.post(sub.url, content=payload_bytes, headers=headers)
                if 200 <= resp.status_code < 300:
                    successful_dispatches += 1
                    logger.info(
                        "webhook_dispatched_successfully",
                        sub_id=sub.id,
                        url=sub.url,
                        status=resp.status_code,
                    )
                else:
                    logger.warning(
                        "webhook_dispatch_non_2xx",
                        sub_id=sub.id,
                        url=sub.url,
                        status=resp.status_code,
                    )
            except Exception as err:
                logger.warning(
                    "webhook_dispatch_failed",
                    sub_id=sub.id,
                    url=sub.url,
                    error=str(err),
                )

        return successful_dispatches
