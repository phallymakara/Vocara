"""API integration tests for Webhook subscription endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhooks_api_crud_flow(async_client: AsyncClient) -> None:
    # 1. Create API key
    key_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "Webhook Tester", "is_live": True},
        headers={"X-Owner-ID": "dev_webhook_user"},
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    # 2. Reject malformed URL
    bad_resp = await async_client.post(
        "/api/v1/webhooks",
        json={"url": "not-a-valid-url"},
        headers=headers,
    )
    assert bad_resp.status_code == 400
    assert bad_resp.json()["error"]["code"] == "INVALID_URL"

    # 3. Register valid webhook
    create_resp = await async_client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://callback.mycompany.com/vocara",
            "event_types": ["job.completed", "job.failed"],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    sub_data = create_resp.json()
    assert sub_data["url"] == "https://callback.mycompany.com/vocara"
    assert sub_data["secret"].startswith("whsec_")
    sub_id = sub_data["id"]

    # 4. List webhooks
    list_resp = await async_client.get("/api/v1/webhooks", headers=headers)
    assert list_resp.status_code == 200
    subs = list_resp.json()
    assert len(subs) == 1
    assert subs[0]["id"] == sub_id

    # 5. Delete webhook
    del_resp = await async_client.delete(f"/api/v1/webhooks/{sub_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # 6. Verify empty list after deletion
    after_list_resp = await async_client.get("/api/v1/webhooks", headers=headers)
    assert after_list_resp.status_code == 200
    assert len(after_list_resp.json()) == 0
