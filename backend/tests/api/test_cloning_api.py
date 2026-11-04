"""API integration tests for Voice Cloning and Voice Design endpoints."""

import io

import pytest
from httpx import AsyncClient

from vocara.utils.audio import generate_synthetic_tone_wav


@pytest.mark.asyncio
async def test_cloning_and_design_api_flow(async_client: AsyncClient) -> None:
    # 1. Create developer key
    key_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "Clone API Tester", "is_live": True},
        headers={"X-Owner-ID": "dev_cloner_1"},
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    sample_wav = generate_synthetic_tone_wav(duration_seconds=1.0, sample_rate=24000)

    # 2. Test clone rejection when consent is false
    no_consent_resp = await async_client.post(
        "/api/v1/voices/clone",
        data={
            "name": "Consentless Voice",
            "consent_confirmed": "false",
            "language": "km-KH",
        },
        files={"file": ("sample.wav", io.BytesIO(sample_wav), "audio/wav")},
        headers=headers,
    )
    assert no_consent_resp.status_code == 400
    assert no_consent_resp.json()["error"]["code"] == "CONSENT_REQUIRED"

    # 3. Test clone rejection when audio data is invalid
    corrupt_audio_resp = await async_client.post(
        "/api/v1/voices/clone",
        data={
            "name": "Corrupt Audio Voice",
            "consent_confirmed": "true",
            "language": "km-KH",
        },
        files={"file": ("corrupt.wav", io.BytesIO(b"NOT_A_REAL_WAV"), "audio/wav")},
        headers=headers,
    )
    assert corrupt_audio_resp.status_code == 422
    assert corrupt_audio_resp.json()["error"]["code"] == "INVALID_AUDIO"

    # 4. Test successful clone with valid WAV and confirmed consent
    clone_resp = await async_client.post(
        "/api/v1/voices/clone",
        data={
            "name": "Dara Cloned",
            "consent_confirmed": "true",
            "language": "km-KH",
            "description": "Developer cloned custom voice",
        },
        files={"file": ("dara.wav", io.BytesIO(sample_wav), "audio/wav")},
        headers=headers,
    )
    assert clone_resp.status_code == 201
    cloned_data = clone_resp.json()
    assert cloned_data["name"] == "Dara Cloned"
    assert cloned_data["voice_type"] == "cloned"
    assert cloned_data["owner_id"] == "dev_cloner_1"
    assert cloned_data["modifiers"]["consent_verified"] is True
    assert "consent_timestamp" in cloned_data["modifiers"]
    cloned_voice_id = cloned_data["id"]

    # 5. Test streaming preview of newly cloned voice
    preview_resp = await async_client.get(
        f"/api/v1/voices/{cloned_voice_id}/preview", headers=headers
    )
    assert preview_resp.status_code == 200
    assert preview_resp.headers["content-type"].startswith("audio/")
    assert len(preview_resp.content) > 0

    # 6. Test design derivative variation based on cloned voice
    design_resp = await async_client.post(
        "/api/v1/voices/design",
        json={
            "name": "Dara High Pitch",
            "base_voice_id": cloned_voice_id,
            "pitch": 1.3,
            "speed": 1.1,
            "emotion": "excited",
            "style": "conversational",
            "description": "Upbeat high-pitch variation of Dara",
        },
        headers=headers,
    )
    assert design_resp.status_code == 201
    designed_data = design_resp.json()
    assert designed_data["name"] == "Dara High Pitch"
    assert designed_data["voice_type"] == "designed"
    assert designed_data["owner_id"] == "dev_cloner_1"
    assert designed_data["modifiers"]["parent_voice_id"] == cloned_voice_id
    assert designed_data["modifiers"]["pitch"] == 1.3
    assert designed_data["modifiers"]["emotion"] == "excited"

    # 7. Test design variation fails with 404 for non-existent base voice
    not_found_design = await async_client.post(
        "/api/v1/voices/design",
        json={
            "name": "Phantom Child",
            "base_voice_id": "non-existent-voice-id",
        },
        headers=headers,
    )
    assert not_found_design.status_code == 404
    assert not_found_design.json()["error"]["code"] == "VOICE_NOT_FOUND"
