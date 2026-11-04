"""Integration test for full asynchronous TTS job processing pipeline with worker."""

import pytest
from httpx import AsyncClient

from vocara.worker.handler import Worker


@pytest.mark.asyncio
async def test_async_tts_worker_lifecycle_e2e(async_client: AsyncClient) -> None:
    # 1. Create API key
    key_resp = await async_client.post(
        "/api/v1/keys",
        json={"name": "Worker E2E Tester", "is_live": True},
        headers={"X-Owner-ID": "dev_e2e_worker_user"},
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    # 2. Seed a voice accessible to caller
    app = async_client._transport.app  # type: ignore[attr-defined]
    container = app.state.container

    from vocara.domain.entities import Voice
    from vocara.domain.enums import VoiceType, VoiceVisibility

    async with container.session_factory() as session:
        voice_repo = container.get_voice_repo(session)
        voice = Voice(
            id="worker-flow-voice-1",
            name="Flow Voice",
            voice_type=VoiceType.BUILT_IN,
            owner_id=None,
            language="km-KH",
            visibility=VoiceVisibility.PUBLIC,
        )
        await voice_repo.create(voice)
        await session.commit()

    # 3. Submit long text (> 2000 characters) to trigger asynchronous job routing
    long_text = "Vocara Voice API Platform delivers real-time voice cloning and Khmer TTS. " * 30
    assert len(long_text) > 2000

    tts_resp = await async_client.post(
        "/api/v1/tts",
        json={
            "text": long_text,
            "voice_id": "worker-flow-voice-1",
            "language": "km-KH",
            "speed": 1.0,
            "output_format": "mp3",
        },
        headers=headers,
    )
    assert tts_resp.status_code == 202
    job_info = tts_resp.json()
    job_id = job_info["id"]
    assert job_info["status"] == "queued"

    # 4. Dequeue task with Worker
    worker = Worker(container)
    assert container.job_queue is not None
    payload = await container.job_queue.dequeue("jobs:inference", timeout_seconds=1)
    assert payload is not None
    assert payload["job_id"] == job_id

    # 4. Worker processes the job
    success = await worker.process_job_payload(payload)
    assert success is True

    # 5. Check job status endpoint -> should now be completed
    status_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["audio_duration_seconds"] > 0.0

    # 6. Download the generated audio via /jobs/{id}/result
    result_resp = await async_client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
    assert result_resp.status_code == 200
    assert result_resp.headers["content-type"] == "audio/mpeg"
    assert len(result_resp.content) > 0
