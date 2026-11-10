"""Unit tests for Modal serverless VoxCPM inference engine adapter."""

import base64

import httpx
import pytest

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, VoiceType, VoiceVisibility
from vocara.infrastructure.inference.modal_engine import ModalInferenceEngine
from vocara.utils.audio import generate_synthetic_tone_wav


@pytest.fixture
def sample_voice() -> Voice:
    return Voice(
        id="test-modal-voice-1",
        name="Modal Test Voice",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        visibility=VoiceVisibility.PUBLIC,
    )


@pytest.mark.asyncio
async def test_modal_engine_unconfigured_url_fails(sample_voice: Voice) -> None:
    """Raises InferenceServiceError if endpoint_url is missing."""
    engine = ModalInferenceEngine(endpoint_url=None)

    with pytest.raises(InferenceServiceError) as exc_info:
        await engine.generate_speech("សួស្តី", sample_voice)

    assert "endpoint URL is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_modal_engine_generate_speech_json_response(sample_voice: Voice) -> None:
    """Correctly parses base64 JSON payload from remote serverless endpoint."""
    raw_wav = generate_synthetic_tone_wav(duration_seconds=1.5, sample_rate=24000)
    b64_audio = base64.b64encode(raw_wav).decode("utf-8")

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/synthesize"
        return httpx.Response(
            200,
            json={"audio_base64": b64_audio, "duration": 1.5},
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = ModalInferenceEngine(
        endpoint_url="https://mock-modal.local",
        api_token="test-modal-token",
        http_client=mock_client,
    )

    audio_bytes, duration = await engine.generate_speech(
        text="សួស្តីពិភពលោក",
        voice=sample_voice,
        output_format=AudioFormat.WAV,
    )

    assert audio_bytes == raw_wav
    assert duration == 1.5


@pytest.mark.asyncio
async def test_modal_engine_generate_speech_binary_response(sample_voice: Voice) -> None:
    """Handles raw audio binary response with X-Audio-Duration header."""
    raw_wav = generate_synthetic_tone_wav(duration_seconds=2.0, sample_rate=24000)

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=raw_wav,
            headers={"Content-Type": "audio/wav", "X-Audio-Duration": "2.0"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = ModalInferenceEngine(
        endpoint_url="https://mock-modal.local",
        http_client=mock_client,
    )

    audio_bytes, duration = await engine.generate_speech(
        text="ការសាកល្បង",
        voice=sample_voice,
        output_format=AudioFormat.WAV,
    )

    assert audio_bytes == raw_wav
    assert duration == 2.0


@pytest.mark.asyncio
async def test_modal_engine_remote_failure_retries(sample_voice: Voice) -> None:
    """Retries transient errors and raises InferenceServiceError on persistent failure."""
    call_count = 0

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, text="Internal Serverless Error")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = ModalInferenceEngine(
        endpoint_url="https://mock-modal.local",
        max_retries=2,
        http_client=mock_client,
    )

    with pytest.raises(InferenceServiceError) as exc_info:
        await engine.generate_speech("តេស្តកំហុស", sample_voice)

    assert "failed after 2 attempts" in str(exc_info.value)
    assert call_count == 2


@pytest.mark.asyncio
async def test_modal_engine_design_preview_calls_design_endpoint(sample_voice: Voice) -> None:
    """Voice Design preview invokes /design cleanly without passing fixed reference WAVs."""
    raw_wav = generate_synthetic_tone_wav(duration_seconds=2.5, sample_rate=48000)
    b64_audio = base64.b64encode(raw_wav).decode("utf-8")
    captured_payload: dict[str, object] = {}

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        import json

        assert request.url.path == "/design"
        captured_payload.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(
            200,
            json={
                "feature_token": "voxcpm_des_abc123",
                "audio_base64": b64_audio,
                "duration": 2.5,
                "control_instruction": "woman, young Cambodian speaker, warm natural pace",
                "prompt_text": "សួស្តី ខ្ញុំ ជា វូការា។",
            },
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)
    engine = ModalInferenceEngine(
        endpoint_url="https://mock-modal.local",
        http_client=mock_client,
        inference_timesteps=20,
        cfg_value=2.0,
    )

    result = await engine.preview_designed_voice(
        base_voice=sample_voice,
        modifiers={
            "gender": "female",
            "description": "A young Cambodian woman speaking warm conversational Khmer.\nAvoid robotic pauses.",
            "emotion": "warm",
            "speed": 1.0,
            "pitch": 1.0,
        },
        preview_text="សួស្តី ខ្ញុំជាវូការា។",
    )

    assert result["audio_bytes"] == raw_wav
    assert result["duration"] == 2.5
    assert "reference_audio_base64" not in captured_payload
    assert captured_payload["preview_text"] == "សួស្តី ខ្ញុំជាវូការា។"
    assert "woman" in str(captured_payload["control_instruction"])
    assert "Avoid robotic pauses" not in str(captured_payload["control_instruction"])


@pytest.mark.asyncio
async def test_modal_engine_synthesize_uses_designed_preview_and_omits_control_when_ref_present() -> None:
    """Designed/cloned voices use their own reference WAV without injecting conflicting control instructions."""
    import json

    class FakeStorage:
        def __init__(self, blobs: dict[str, bytes]) -> None:
            self.blobs = blobs

        async def download(self, key: str) -> bytes:
            return self.blobs[key]

    own_preview = generate_synthetic_tone_wav(duration_seconds=1.2, sample_rate=48000, frequency=240.0)
    parent_ref = generate_synthetic_tone_wav(duration_seconds=1.2, sample_rate=48000, frequency=180.0)
    out_wav = generate_synthetic_tone_wav(duration_seconds=1.5, sample_rate=48000, frequency=240.0)
    captured: dict[str, object] = {}

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(
            200,
            json={"audio_base64": base64.b64encode(out_wav).decode("utf-8"), "duration": 1.5},
            headers={"Content-Type": "application/json"},
        )

    designed_voice = Voice(
        id="designed-123",
        name="Young Woman",
        voice_type=VoiceType.DESIGNED,
        owner_id="user-1",
        language="km",
        description="Young Cambodian woman",
        reference_audio_key="voices/voice-sophea-built-in/preview.wav",
        preview_audio_key="voices/designed-123/preview.wav",
        modifiers={"gender": "female", "pitch": 1.2, "prompt_text": "សួស្តី"},
        visibility=VoiceVisibility.PRIVATE,
    )
    engine = ModalInferenceEngine(
        endpoint_url="https://mock-modal.local",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)),
        storage=FakeStorage(
            {
                "voices/designed-123/preview.wav": own_preview,
                "voices/voice-sophea-built-in/preview.wav": parent_ref,
            }
        ),
    )

    audio_bytes, duration = await engine.generate_speech(
        text="សួស្តីបង!",
        voice=designed_voice,
        output_format=AudioFormat.WAV,
    )

    assert duration == 1.5
    assert audio_bytes == out_wav
    assert captured["reference_audio_key"] == "voices/designed-123/preview.wav"
    assert captured["reference_audio_base64"] == base64.b64encode(own_preview).decode("utf-8")
    assert captured["control_instruction"] is None
    assert captured["prompt_text"] is None
