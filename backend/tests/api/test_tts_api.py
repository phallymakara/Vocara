"""API integration tests for /api/v1/tts and /api/v1/jobs endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tts_and_jobs_api_full_flow(async_client: AsyncClient) -> None:
    # 1. Create API Key
    key_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "TTS Key", "is_live": True},
        headers={"X-Owner-ID": "dev_tts_user"},
    )
    raw_api_key = key_resp.json()["api_key"]
    headers = {"Authorization": f"Bearer {raw_api_key}"}

    # 2. Seed a voice into test DB
    from vocara.domain.entities import Voice
    from vocara.domain.enums import JobStatus, VoiceType, VoiceVisibility

    app = async_client._transport.app  # type: ignore[attr-defined]
    container = app.state.container
    async with container.session_factory() as session:
        v_repo = container.get_voice_repo(session)
        seeded_voice = Voice(
            id="tts-test-voice-1",
            name="Sophea TTS Voice",
            voice_type=VoiceType.BUILT_IN,
            owner_id=None,
            language="km-KH",
            visibility=VoiceVisibility.PUBLIC,
        )
        await v_repo.create(seeded_voice)
        await session.commit()

    # 3. Synchronous TTS Request (< 250 characters)
    short_text = "សួស្តី Vocara API"
    sync_resp = await async_client.post(
        "/api/v1/tts",
        json={
            "text": short_text,
            "voice_id": "tts-test-voice-1",
            "language": "km-KH",
            "output_format": "mp3",
        },
        headers=headers,
    )
    assert sync_resp.status_code == 200
    assert sync_resp.headers["content-type"] in ("audio/mpeg", "audio/mp3")
    assert "X-Audio-Duration" in sync_resp.headers
    assert len(sync_resp.content) > 100

    # 4. Asynchronous TTS Request (>= 2000 characters)
    long_text = "អត្ថបទវែង សម្រាប់ធ្វើតេស្តការងារផ្ទៃខាងក្រោយ " * 60
    async_resp = await async_client.post(
        "/api/v1/tts",
        json={
            "text": long_text,
            "voice_id": "tts-test-voice-1",
            "language": "km-KH",
            "output_format": "mp3",
        },
        headers=headers,
    )
    assert async_resp.status_code == 202
    job_data = async_resp.json()
    assert "id" in job_data
    job_id = job_data["id"]
    assert job_data["status"] == "queued"
    assert "Location" in async_resp.headers

    # 5. Poll Job Status
    job_status_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_status_resp.status_code == 200
    assert job_status_resp.json()["id"] == job_id
    assert job_status_resp.json()["status"] == "queued"

    # 6. Attempt download before completion -> returns 500/409 (Job in progress)
    result_early = await async_client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
    assert result_early.status_code != 200

    # 7. Complete job in DB and upload mock audio artifact
    audio_key = f"audio/jobs/{job_id}.mp3"
    await container.storage.upload(audio_key, b"fake-job-mp3-data", content_type="audio/mpeg")
    async with container.session_factory() as session:
        j_repo = container.get_job_repo(session)
        await j_repo.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            output_audio_key=audio_key,
            duration_seconds=4.2,
        )
        await session.commit()

    # 8. Download completed job audio artifact
    result_resp = await async_client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
    assert result_resp.status_code == 200
    assert result_resp.content == b"fake-job-mp3-data"
    assert result_resp.headers["content-type"] in ("audio/mpeg", "audio/mp3")
