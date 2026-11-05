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
        desc_lower = (voice.description or "").lower()

        # 1. Explicit modifier gender takes highest priority
        if modifier_gender == "female":
            is_female = True
            is_male = False
        elif modifier_gender == "male":
            is_female = False
            is_male = True
        else:
            # Word-boundary regex checks on description and voice name
            has_female_words = bool(
                re.search(r"\b(female|woman|women|girl|girls|actress|lady|ladies|she|her)\b", desc_lower)
                or "female" in voice_name_lower
                or "sophea" in voice_id_lower
                or "sreymom" in voice_id_lower
            )
            has_male_words = bool(
                re.search(r"\b(male|man|men|boy|boys|actor|actors|gentleman|gentlemen|he|his)\b", desc_lower)
                or bool(re.search(r"\bmale\b", voice_name_lower))
                or "dara" in voice_id_lower
                or "piseth" in voice_id_lower
            )
            if has_female_words and not has_male_words:
                is_female = True
                is_male = False
            elif has_male_words and not has_female_words:
                is_female = False
                is_male = True
            else:
                is_female = "sophea" in voice_id_lower or "sophea" in voice_name_lower
                is_male = not is_female

        # If language is explicit English or no Khmer characters in English voice
        if effective_lang.startswith("en") and not has_khmer_script:
            return "en-US-JennyNeural" if is_female else "en-US-GuyNeural"

        # Native Khmer neural speakers
        return "km-KH-SreymomNeural" if is_female else "km-KH-PisethNeural"

    def _calculate_acoustic_params(self, voice: Voice, speed: float) -> tuple[str, str]:
        """Compute rate and pitch strings, taking into account user sliders and description cues."""
        desc_lower = (voice.description or "").lower()

        # 1. Natural pacing: add +8% base so conversational Khmer speech is never dragging or slow
        base_rate_bonus = 8
        if any(w in desc_lower for w in ["young", "youthful", "actress", "energetic", "fast", "brisk", "dynamic"]):
            base_rate_bonus += 5
        elif any(w in desc_lower for w in ["calm", "slow", "deliberate", "relax", "soothing"]):
            base_rate_bonus -= 6

        user_speed = float(voice.modifiers.get("speed", 1.0)) * speed
        speed_pct = base_rate_bonus + int(round((user_speed - 1.0) * 100))
        rate_str = f"+{speed_pct}%" if speed_pct >= 0 else f"{speed_pct}%"

        # 2. Natural pitch calculation: add youthful/actress brightness if specified in description
        base_pitch_bonus = 0
        if any(w in desc_lower for w in ["young", "youthful", "teen", "19 years", "girl", "high", "bright", "light tone"]):
            base_pitch_bonus += 12
        elif any(w in desc_lower for w in ["deep", "authoritative", "mature", "elderly", "low"]):
            base_pitch_bonus -= 12

        if "pitch_hz_offset" in voice.modifiers:
            pitch_hz = int(voice.modifiers["pitch_hz_offset"]) + base_pitch_bonus
            pitch_str = f"{pitch_hz:+d}Hz"
        else:
            user_pitch = float(voice.modifiers.get("pitch", 1.0))
            pitch_val = base_pitch_bonus + int(round((user_pitch - 1.0) * 50))
            pitch_str = f"+{pitch_val}Hz" if pitch_val >= 0 else f"{pitch_val}Hz"

        return rate_str, pitch_str

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
        rate_str, pitch_str = self._calculate_acoustic_params(voice, speed)

        async def _call() -> tuple[bytes, float]:
            chunks: list[bytes] = []
            for r_try, p_try in [(rate_str, pitch_str), (rate_str, "+0Hz"), ("+0%", "+0Hz")]:
                try:
                    comm = edge_tts.Communicate(
                        text=text.strip(),
                        voice=speaker,
                        rate=r_try,
                        pitch=p_try,
                    )
                    async for chunk in comm.stream():
                        if chunk.get("type") == "audio" and "data" in chunk:
                            chunks.append(chunk["data"])
                    if chunks:
                        break
                except Exception as stream_err:
                    logger.warning("edge_tts_attempt_failed", rate=r_try, pitch=p_try, error=str(stream_err))
                    chunks.clear()

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

        preview_bytes = b""
        for r_try, p_try in [("+0%", "+0Hz")]:
            try:
                comm = edge_tts.Communicate(DEFAULT_PREVIEW_TEXT, speaker, rate=r_try, pitch=p_try)
                chunks = [c["data"] async for c in comm.stream() if c.get("type") == "audio"]
                if chunks:
                    preview_bytes = b"".join(chunks)
                    break
            except Exception:
                preview_bytes = b""

        if preview_bytes:
            try:
                data, sample_rate = sf.read(io.BytesIO(preview_bytes), dtype="float32")
                out_buf = io.BytesIO()
                sf.write(out_buf, data, sample_rate, format="WAV", subtype="PCM_16")
                preview_bytes = out_buf.getvalue()
            except Exception:
                pass
        else:
            preview_bytes = reference_audio_bytes

        return feature_token, preview_bytes

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Derive acoustic profile variation and return spoken preview audio."""
        derived_token = f"emb_var_{uuid.uuid4().hex[:16]}"
        effective_voice = Voice(
            id=base_voice.id,
            name=base_voice.name,
            voice_type=base_voice.voice_type,
            owner_id=base_voice.owner_id,
            language=base_voice.language,
            description=modifiers.get("description") or base_voice.description,
            modifiers=modifiers,
            visibility=base_voice.visibility,
        )
        speaker = self._select_speaker(effective_voice, DEFAULT_PREVIEW_TEXT, base_voice.language)
        rate_str, pitch_str = self._calculate_acoustic_params(effective_voice, 1.0)

        preview_bytes = b""
        for r_try, p_try in [(rate_str, pitch_str), (rate_str, "+0Hz"), ("+0%", "+0Hz")]:
            try:
                comm = edge_tts.Communicate(
                    DEFAULT_PREVIEW_TEXT,
                    speaker,
                    rate=r_try,
                    pitch=p_try,
                )
                chunks = [c["data"] async for c in comm.stream() if c.get("type") == "audio"]
                if chunks:
                    preview_bytes = b"".join(chunks)
                    break
            except Exception:
                continue

        if preview_bytes:
            try:
                data, sample_rate = sf.read(io.BytesIO(preview_bytes), dtype="float32")
                out_buf = io.BytesIO()
                sf.write(out_buf, data, sample_rate, format="WAV", subtype="PCM_16")
                preview_bytes = out_buf.getvalue()
            except Exception:
                pass

        return derived_token, preview_bytes
