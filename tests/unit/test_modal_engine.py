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
