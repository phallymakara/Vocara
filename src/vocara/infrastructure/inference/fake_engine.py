"""Mock/Fake inference engine for local development and fast automated testing."""

import uuid
from typing import Any

from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import generate_synthetic_tone_wav


class FakeInferenceEngine(BaseInferenceEngine):
    """Fast, local synthetic engine implementing InferenceEngine without GPU requirements."""

    def __init__(self, sample_rate: int = 24000) -> None:
        super().__init__(timeout_seconds=5, max_retries=1)
        self.sample_rate = sample_rate

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
    ) -> tuple[bytes, float]:
        """Generate realistic synthetic WAV/audio bytes based on text length."""
        # Estimate duration: ~15 chars per second adjusted for speed
        char_count = max(1, len(text))
        duration = max(0.5, round((char_count / 15.0) / max(0.5, speed), 2))

        # Different frequencies based on voice name for audible distinction
        base_freq = 440.0 + (hash(voice.name) % 150)
        audio_bytes = generate_synthetic_tone_wav(
            duration_seconds=min(duration, 5.0),  # Cap generated wave for speed
            sample_rate=self.sample_rate,
            frequency=base_freq,
        )

        return audio_bytes, duration

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
    ) -> tuple[str, bytes]:
        """Simulate extracting vocal embeddings and producing a preview sample."""
        feature_token = f"emb_{uuid.uuid4().hex[:16]}"
        preview_sample = generate_synthetic_tone_wav(
            duration_seconds=1.5,
            sample_rate=self.sample_rate,
            frequency=520.0,
        )
        return feature_token, preview_sample

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Simulate deriving a modified voice profile and returning preview."""
        derived_token = f"emb_var_{uuid.uuid4().hex[:16]}"
        preview_sample = generate_synthetic_tone_wav(
            duration_seconds=1.5,
            sample_rate=self.sample_rate,
            frequency=480.0,
        )
        return derived_token, preview_sample
