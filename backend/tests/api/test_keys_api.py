"""API endpoint tests for API keys and usage tracking."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_keys_api_full_flow(async_client: AsyncClient) -> None:
    # 1. Unauthenticated request to /api/v1/keys should be rejected (401)
    unauthed_resp = await async_client.get("/api/v1/keys")
    assert unauthed_resp.status_code == 401
    assert unauthed_resp.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Create an API key
    create_resp = await async_client.post(
        "/api/v1/keys",
        json={
            "name": "Integration Test Key",
            "is_live": True,
            "rate_limit_per_minute": 100,
            "char_quota_per_month": 50000,
        },
        headers={"X-Owner-ID": "test_developer_1"},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert "api_key" in data
    raw_api_key = data["api_key"]
    key_id = data["id"]
    assert raw_api_key.startswith("voc_live_")

    # 3. List keys using Bearer token authentication
    list_resp = await async_client.get(
        "/api/v1/keys",
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert list_resp.status_code == 200
    keys_list = list_resp.json()
    assert len(keys_list) >= 1
    assert any(k["id"] == key_id for k in keys_list)

    # 4. Check usage endpoint
    usage_resp = await async_client.get(
        "/api/v1/usage",
        headers={"X-API-Key": raw_api_key},
    )
    assert usage_resp.status_code == 200
    usage_data = usage_resp.json()
    assert usage_data["owner_id"] == "test_developer_1"
    assert usage_data["characters_used"] == 0
    assert usage_data["total_quota"] == 50000

    # 5. Update key name
    patch_resp = await async_client.patch(
        f"/api/v1/keys/{key_id}",
        json={"name": "Renamed Integration Key"},
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed Integration Key"

    # 6. Create a second key so we can test permanent delete cleanly
    second_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "Secondary Key", "is_live": True},
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert second_resp.status_code == 201
    second_id = second_resp.json()["id"]

    delete_resp = await async_client.delete(
        f"/api/v1/keys/{second_id}?permanent=true",
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    # 7. Revoke key
    revoke_resp = await async_client.delete(
        f"/api/v1/keys/{key_id}",
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"

    # 8. Once revoked, authenticating with this key returns 401
    revoked_lookup = await async_client.get(
        "/api/v1/keys",
        headers={"Authorization": f"Bearer {raw_api_key}"},
    )
    assert revoked_lookup.status_code == 401
