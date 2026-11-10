"""Mock/Fake inference engine for local development and fast automated testing."""

import uuid
from typing import Any

from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import estimate_pitch_or_centroid, generate_synthetic_tone_wav


class FakeInferenceEngine(BaseInferenceEngine):
    """Fast, local synthetic engine implementing InferenceEngine with VoxCPM acoustic profile emulation."""

    def __init__(
        self,
        sample_rate: int = 24000,
        storage: BlobStorage | None = None,
    ) -> None:
        super().__init__(timeout_seconds=5, max_retries=1)
        self.sample_rate = sample_rate
        self.storage = storage

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Generate realistic synthetic WAV/audio bytes based on text length and voice parameters."""
        char_count = max(1, len(text))
        voice_speed = float(voice.modifiers.get("speed", 1.0))
        effective_speed = max(0.5, speed * voice_speed)
        duration = max(0.5, round((char_count / 15.0) / effective_speed, 2))

        voice_type_val = getattr(voice.voice_type, "value", str(voice.voice_type)).lower()

        # Determine acoustic base frequency
        if voice_type_val == "cloned" and self.storage and voice.reference_audio_key:
            try:
                ref_bytes = await self.storage.download(voice.reference_audio_key)
                base_freq = estimate_pitch_or_centroid(ref_bytes)
            except Exception:
                token = str(voice.modifiers.get("feature_token", ""))
                base_freq = 200.0 + (hash(token) % 60 - 30)
        elif voice_type_val == "designed":
            desc_lower = (voice.description or "").lower()
            name_lower = voice.name.lower()

            if "female" in desc_lower or "female" in name_lower or "sophea" in name_lower:
                base_freq = 260.0
            elif "male" in desc_lower or "male" in name_lower or "dara" in name_lower:
                base_freq = 175.0
            elif "child" in desc_lower or "young" in desc_lower or "bright" in desc_lower:
                base_freq = 310.0
            elif "elderly" in desc_lower or "deep" in desc_lower or "authoritative" in desc_lower:
                base_freq = 135.0
            else:
                base_freq = 210.0

            # Inherit reference audio base pitch if cloned parent was used
            if self.storage and voice.reference_audio_key:
                try:
                    ref_bytes = await self.storage.download(voice.reference_audio_key)
                    base_freq = estimate_pitch_or_centroid(ref_bytes)
                except Exception:
                    pass
        else:
            name_lower = voice.name.lower()
            if "female" in name_lower or "sophea" in name_lower:
                base_freq = 260.0
            elif "male" in name_lower or "dara" in name_lower:
                base_freq = 180.0
            elif "alex" in name_lower:
                base_freq = 210.0
            else:
                base_freq = 220.0 + (hash(voice.name) % 40)

        # Apply Voice Design pitch modifier
        pitch_factor = float(voice.modifiers.get("pitch", 1.0))
        effective_freq = max(80.0, min(800.0, base_freq * pitch_factor))

        audio_bytes = generate_synthetic_tone_wav(
            duration_seconds=min(duration, 10.0),
            sample_rate=self.sample_rate,
            frequency=effective_freq,
        )

        return audio_bytes, duration

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
        prompt_text: str | None = None,
        voice_id: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, bytes]:
        """Simulate extracting vocal embeddings and producing a preview sample."""
        feature_token = f"emb_{uuid.uuid4().hex[:16]}"
        detected_pitch = estimate_pitch_or_centroid(reference_audio_bytes)
        preview_sample = generate_synthetic_tone_wav(
            duration_seconds=1.5,
            sample_rate=self.sample_rate,
            frequency=detected_pitch,
        )
        return feature_token, preview_sample

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
        preview_text: str | None = None,
    ) -> tuple[str, bytes]:
        """Simulate deriving a modified voice profile and returning preview."""
        derived_token = f"emb_var_{uuid.uuid4().hex[:16]}"
        pitch_factor = float(modifiers.get("pitch", 1.0))
        base_freq = 240.0 if "female" in base_voice.name.lower() else 180.0
        effective_freq = max(80.0, min(800.0, base_freq * pitch_factor))
        preview_sample = generate_synthetic_tone_wav(
            duration_seconds=1.5,
            sample_rate=self.sample_rate,
            frequency=effective_freq,
        )
        return derived_token, preview_sample
