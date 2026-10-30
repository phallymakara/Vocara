"""API integration tests for Voice Library endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voices_api_full_flow(async_client: AsyncClient) -> None:
    # 1. Create developer key
    key_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "Voice API Tester", "is_live": True},
        headers={"X-Owner-ID": "dev_voice_user"},
    )
    assert key_resp.status_code == 201
    raw_api_key = key_resp.json()["api_key"]
    headers = {"Authorization": f"Bearer {raw_api_key}"}

    # 2. List voices initially
    list_resp = await async_client.get("/api/v1/voices", headers=headers)
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)

    # 3. Create a custom voice directly in repo or test 404 for non-existent
    not_found = await async_client.get("/api/v1/voices/non-existent-id", headers=headers)
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "VOICE_NOT_FOUND"

    # 4. Preview stream test with fallback tone
    # Let's seed a voice in DB to preview
    # (Since clone endpoint is in Phase 5, let's insert a test voice using the active DB session)
    from vocara.domain.entities import Voice
    from vocara.domain.enums import VoiceType, VoiceVisibility

    # Access container from app
    app = async_client._transport.app  # type: ignore[attr-defined]
    container = app.state.container
    async with container.session_factory() as session:
        repo = container.get_voice_repo(session)
        seeded = Voice(
            id="test-voice-preview-1",
            name="Sophea Seeded Voice",
            voice_type=VoiceType.CLONED,
            owner_id="dev_voice_user",
            language="km-KH",
            visibility=VoiceVisibility.PRIVATE,
        )
        await repo.create(seeded)
        await session.commit()

    # 5. Fetch seeded voice
    get_resp = await async_client.get("/api/v1/voices/test-voice-preview-1", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Sophea Seeded Voice"

    # 6. Patch voice
    patch_resp = await async_client.patch(
        "/api/v1/voices/test-voice-preview-1",
        json={"name": "Sophea Updated", "description": "High quality natural voice"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Sophea Updated"
    assert patch_resp.json()["description"] == "High quality natural voice"

    # 7. Preview stream audio
    preview_resp = await async_client.get(
        "/api/v1/voices/test-voice-preview-1/preview", headers=headers
    )
    assert preview_resp.status_code == 200
    assert preview_resp.headers["content-type"] in ("audio/wav", "audio/x-wav")
    assert len(preview_resp.content) > 100

    # 8. Delete voice
    del_resp = await async_client.delete("/api/v1/voices/test-voice-preview-1", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Subsequent fetch should be 404
    after_del = await async_client.get("/api/v1/voices/test-voice-preview-1", headers=headers)
    assert after_del.status_code == 404
