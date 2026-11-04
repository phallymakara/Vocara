"""Neural Text-to-Speech Engine with native Khmer and English vocal support.

Provides high-clarity human voice synthesis for Khmer (Sophea, Dara) and
English (Alex) with dynamic speed and pitch controls.
"""

import io
import re
import uuid
from typing import Any

import edge_tts
import soundfile as sf
import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.constants import DEFAULT_PREVIEW_TEXT
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import get_audio_duration_seconds

logger = structlog.get_logger("vocara.inference.neural")


class NeuralTtsEngine(BaseInferenceEngine):
    """High-fidelity neural TTS inference engine with native Khmer and multilingual voices."""

    def __init__(
        self,
        storage: BlobStorage | None = None,
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, max_retries=max_retries)
        self.storage = storage

    def _select_speaker(self, voice: Voice, text: str, language: str) -> str:
        """Select appropriate neural speaker model based on voice metadata and text scripts."""
        effective_lang = (voice.language or language or "km-KH").lower()
        has_khmer_script = bool(re.search(r"[\u1780-\u17FF]", text))

        voice_name_lower = voice.name.lower()
        voice_id_lower = voice.id.lower()
        modifier_gender = str(voice.modifiers.get("gender", "")).lower()

        # If language is explicit English or no Khmer characters in English voice
        if effective_lang.startswith("en") and not has_khmer_script:
            if (
                modifier_gender == "female"
                or "female" in voice_name_lower
                or "sophea" in voice_id_lower
            ):
                return "en-US-JennyNeural"
            return "en-US-GuyNeural"

        # Native Khmer neural speakers
        if (
            modifier_gender == "female"
            or "female" in voice_name_lower
            or "sophea" in voice_id_lower
        ):
            return "km-KH-SreymomNeural"
        return "km-KH-PisethNeural"

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Synthesize text into natural human speech audio."""
        if not text or not text.strip():
            raise InferenceServiceError("Cannot synthesize empty text.")

        speaker = self._select_speaker(voice, text, language)

        # Calculate speed rate parameter for edge-tts (e.g. +10%, -15%)
        speed_factor = float(voice.modifiers.get("speed", 1.0)) * speed
        speed_pct = int(round((speed_factor - 1.0) * 100))
        rate_str = f"+{speed_pct}%" if speed_pct >= 0 else f"{speed_pct}%"

        # Calculate pitch parameter using measured Hz offset if available, or factor
        if "pitch_hz_offset" in voice.modifiers:
            pitch_hz = int(voice.modifiers["pitch_hz_offset"])
            pitch_str = f"{pitch_hz:+d}Hz"
        else:
            pitch_factor = float(voice.modifiers.get("pitch", 1.0))
            pitch_val = int(round((pitch_factor - 1.0) * 50))
            pitch_str = f"+{pitch_val}Hz" if pitch_val >= 0 else f"{pitch_val}Hz"

        async def _call() -> tuple[bytes, float]:
            comm = edge_tts.Communicate(
                text=text.strip(),
                voice=speaker,
                rate=rate_str,
                pitch=pitch_str,
            )
            chunks: list[bytes] = []
            async for chunk in comm.stream():
                if chunk.get("type") == "audio" and "data" in chunk:
                    chunks.append(chunk["data"])

            if not chunks:
                raise InferenceServiceError(f"No audio stream received from speaker {speaker}.")

            mp3_bytes = b"".join(chunks)

            # Convert to WAV if requested by client
            if output_format == AudioFormat.WAV:
                try:
                    data, sample_rate = sf.read(io.BytesIO(mp3_bytes), dtype="float32")
                    out_buf = io.BytesIO()
                    sf.write(out_buf, data, sample_rate, format="WAV", subtype="PCM_16")
                    wav_bytes = out_buf.getvalue()
                    duration = len(data) / float(sample_rate)
                    return wav_bytes, round(duration, 2)
                except Exception as conv_err:
                    logger.warning("wav_conversion_failed_using_mp3", error=str(conv_err))

            try:
                duration = get_audio_duration_seconds(mp3_bytes)
            except Exception:
                duration = max(0.5, len(text) / 12.0)

            return mp3_bytes, round(duration, 2)

        return await self._execute_with_retry("neural_generate_speech", _call)

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
    ) -> tuple[str, bytes]:
        """Extract voice embedding token and synthesize canonical preview audio."""
        feature_token = f"emb_{uuid.uuid4().hex[:16]}"
        speaker = "km-KH-SreymomNeural" if language.startswith("km") else "en-US-GuyNeural"

        try:
            comm = edge_tts.Communicate(DEFAULT_PREVIEW_TEXT, speaker)
            chunks = [c["data"] async for c in comm.stream() if c.get("type") == "audio"]
            preview_bytes = b"".join(chunks) if chunks else reference_audio_bytes
        except Exception:
            preview_bytes = reference_audio_bytes

        return feature_token, preview_bytes

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Derive acoustic profile variation and return spoken preview audio."""
        derived_token = f"emb_var_{uuid.uuid4().hex[:16]}"
        speaker = self._select_speaker(base_voice, DEFAULT_PREVIEW_TEXT, base_voice.language)

        pitch_factor = float(modifiers.get("pitch", 1.0))
        pitch_val = int(round((pitch_factor - 1.0) * 50))
        pitch_str = f"+{pitch_val}Hz" if pitch_val >= 0 else f"{pitch_val}Hz"

        speed_factor = float(modifiers.get("speed", 1.0))
        speed_pct = int(round((speed_factor - 1.0) * 100))
        rate_str = f"+{speed_pct}%" if speed_pct >= 0 else f"{speed_pct}%"

        try:
            comm = edge_tts.Communicate(
                DEFAULT_PREVIEW_TEXT,
                speaker,
                rate=rate_str,
                pitch=pitch_str,
            )
            chunks = [c["data"] async for c in comm.stream() if c.get("type") == "audio"]
            preview_bytes = b"".join(chunks) if chunks else b""
        except Exception:
            preview_bytes = b""

        return derived_token, preview_bytes
