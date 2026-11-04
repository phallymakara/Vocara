"""Unit tests for Hugging Face VoxCPM inference engine adapter."""

import base64

import httpx
import pytest

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.infrastructure.inference.huggingface_engine import HuggingFaceInferenceEngine
from vocara.utils.audio import generate_synthetic_tone_wav


@pytest.fixture
def sample_voice() -> Voice:
    return Voice(
        id="test-hf-voice-1",
        name="HF Test Voice",
        voice_type=VoiceType.BUILT_IN,
        owner_id=None,
        language="km-KH",
        visibility=VoiceVisibility.PUBLIC,
    )


@pytest.mark.asyncio
async def test_hf_engine_unconfigured_url_fails(sample_voice: Voice) -> None:
    """Raises InferenceServiceError if endpoint_url is missing."""
    engine = HuggingFaceInferenceEngine(endpoint_url=None)

    with pytest.raises(InferenceServiceError) as exc_info:
        await engine.generate_speech("Hello", sample_voice)

    assert "endpoint URL is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hf_engine_generate_speech_json_response(sample_voice: Voice) -> None:
    """Correctly parses base64 JSON payload from Hugging Face endpoint."""
    raw_wav = generate_synthetic_tone_wav(duration_seconds=1.5, sample_rate=24000)
    b64_audio = base64.b64encode(raw_wav).decode("utf-8")

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "Bearer hf_test_token" in request.headers["Authorization"]
        return httpx.Response(
            200,
            json={"audio_base64": b64_audio, "duration": 1.5},
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = HuggingFaceInferenceEngine(
        endpoint_url="https://mock-hf.endpoints.huggingface.cloud",
        api_token="hf_test_token",
        http_client=mock_client,
    )

    audio_bytes, duration = await engine.generate_speech("Hello from HF", sample_voice)
    assert audio_bytes == raw_wav
    assert duration == 1.5


@pytest.mark.asyncio
async def test_hf_engine_clone_voice(sample_voice: Voice) -> None:
    """Dispatches audio to clone endpoint on Hugging Face."""
    input_audio = generate_synthetic_tone_wav(duration_seconds=1.0)
    preview_audio = generate_synthetic_tone_wav(duration_seconds=1.2)
    b64_preview = base64.b64encode(preview_audio).decode("utf-8")

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/clone"
        return httpx.Response(
            200,
            json={"feature_token": "emb_hf_12345", "preview_base64": b64_preview},
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = HuggingFaceInferenceEngine(
        endpoint_url="https://mock-hf.endpoints.huggingface.cloud",
        api_token="hf_test_token",
        http_client=mock_client,
    )

    token, preview = await engine.clone_voice(input_audio, language="km-KH")
    assert token == "emb_hf_12345"
    assert preview == preview_audio


@pytest.mark.asyncio
async def test_hf_engine_with_cloned_voice_forwards_reference_audio() -> None:
    """Ensures reference audio sample is downloaded and sent in VoxCPM payload."""
    from vocara.infrastructure.storage.local import LocalStorageAdapter
    import tempfile
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(tmpdir)
        ref_wav = generate_synthetic_tone_wav(duration_seconds=1.0)
        ref_key = "voices/test-cloned/reference.wav"
        await storage.upload(ref_key, ref_wav, content_type="audio/wav")

        cloned_voice = Voice(
            id="test-cloned-id",
            name="My Cloned Voice",
            voice_type=VoiceType.CLONED,
            owner_id="user-1",
            language="km-KH",
            reference_audio_key=ref_key,
        )

        captured_payload: dict = {}

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_payload
            captured_payload = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={"audio_base64": base64.b64encode(ref_wav).decode("utf-8"), "duration": 1.0},
                headers={"Content-Type": "application/json"},
            )

        transport = httpx.MockTransport(mock_handler)
        mock_client = httpx.AsyncClient(transport=transport)

        engine = HuggingFaceInferenceEngine(
            endpoint_url="https://mock-hf.endpoints.huggingface.cloud",
            http_client=mock_client,
            storage=storage,
        )

        audio_bytes, duration = await engine.generate_speech("Testing clone", cloned_voice)
        assert audio_bytes == ref_wav
        assert captured_payload["voice_type"] == "cloned"
        assert captured_payload["reference_audio_base64"] == base64.b64encode(ref_wav).decode("utf-8")


@pytest.mark.asyncio
async def test_hf_engine_with_designed_voice_builds_voxcpm_instruction() -> None:
    """Ensures Voice Design parameters are formatted as VoxCPM style instructions."""
    import json

    designed_voice = Voice(
        id="test-designed-id",
        name="Soothing Storyteller",
        voice_type=VoiceType.DESIGNED,
        owner_id="user-1",
        language="km-KH",
        description="Warm, calm female voice",
        modifiers={"pitch": 1.2, "speed": 0.9, "emotion": "joyful"},
    )

    captured_payload: dict = {}

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content.decode("utf-8"))
        raw = generate_synthetic_tone_wav(duration_seconds=1.0)
        return httpx.Response(
            200,
            json={"audio_base64": base64.b64encode(raw).decode("utf-8"), "duration": 1.0},
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    engine = HuggingFaceInferenceEngine(
        endpoint_url="https://mock-hf.endpoints.huggingface.cloud",
        http_client=mock_client,
    )

    await engine.generate_speech("Synthesize this story", designed_voice)
    assert "Warm, calm female voice" in captured_payload["control_instruction"]
    assert "pitch: 1.2x" in captured_payload["control_instruction"]
    assert "speed: 0.9x" in captured_payload["control_instruction"]
    assert "emotion: joyful" in captured_payload["control_instruction"]
    assert captured_payload["inputs"].startswith("(")
    assert "Synthesize this story" in captured_payload["inputs"]


@pytest.mark.asyncio
async def test_hf_engine_fallback_when_remote_fails(sample_voice: Voice) -> None:
    """Gracefully falls back to local engine when remote VoxCPM endpoint fails."""
    from vocara.infrastructure.inference.fake_engine import FakeInferenceEngine

    async def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Space is sleeping")

    transport = httpx.MockTransport(failing_handler)
    mock_client = httpx.AsyncClient(transport=transport)
    fallback = FakeInferenceEngine()

    engine = HuggingFaceInferenceEngine(
        endpoint_url="https://mock-hf.endpoints.huggingface.cloud",
        http_client=mock_client,
        fallback_engine=fallback,
    )

    audio_bytes, duration = await engine.generate_speech("Fallback test", sample_voice)
    assert len(audio_bytes) > 0
    assert duration > 0

