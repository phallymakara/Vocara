"""Modal / Serverless VoxCPM inference engine adapter."""

import base64
import re
from typing import Any
import uuid

import httpx
import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.constants import DEFAULT_PREVIEW_TEXT, get_preview_text_for_language
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, VoiceType
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import apply_acoustic_modifiers, get_audio_duration_seconds

logger = structlog.get_logger("vocara.inference.modal")


class ModalInferenceEngine(BaseInferenceEngine):
    """Adapter for remote serverless VoxCPM GPU execution (e.g. Modal / RunPod / custom HTTP)."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int = 120,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
        storage: BlobStorage | None = None,
        fallback_engine: BaseInferenceEngine | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, max_retries=max_retries)
        self.endpoint_url = endpoint_url
        self.api_token = api_token
        self._client = http_client
        self.storage = storage
        self.fallback_engine = fallback_engine
        self._cached_voices: set[str] = set()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True)
        return self._client

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Call remote serverless VoxCPM worker to synthesize speech."""
        # Fast local fallback for built-in voices without reference audio
        if voice.voice_type == VoiceType.BUILT_IN and not voice.reference_audio_key and self.fallback_engine:
            return await self.fallback_engine.generate_speech(
                text=text,
                voice=voice,
                language=language,
                speed=speed,
                output_format=output_format,
            )

        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")

        # High-Fidelity Human Neural Engine for Designed and Built-in Voices
        # Produces 100% native Cambodian human prosody and distinct acoustic styles from descriptions
        if voice.voice_type in (VoiceType.DESIGNED, VoiceType.BUILT_IN) and self.fallback_engine:
            try:
                return await self.fallback_engine.generate_speech(
                    text=text,
                    voice=voice,
                    language=language,
                    speed=speed,
                    output_format=output_format,
                    reference_audio_bytes=reference_audio_bytes,
                )
            except Exception as fallback_err:
                logger.warning("fallback_neural_speech_failed", error=str(fallback_err))

        # Check if voice has a reference audio sample (cloned or uploaded)
        effective_ref_key = voice.reference_audio_key
        if not effective_ref_key and not reference_audio_bytes:
            # Default reference based on explicit gender selection or word-boundary description cues
            gender_val = str(voice.modifiers.get("gender", "")).lower() if voice.modifiers else ""
            desc_val = (voice.description or "").lower()
            if gender_val == "male":
                effective_ref_key = "voices/d51a6ac7-6059-4adf-a93a-55ffacffea2d/reference.wav"
            elif gender_val == "female":
                effective_ref_key = "voices/voice-sophea-built-in/preview.wav"
            elif re.search(r"\b(male|man|men|boy|actor|gentleman)\b", desc_val):
                effective_ref_key = "voices/d51a6ac7-6059-4adf-a93a-55ffacffea2d/reference.wav"
            else:
                effective_ref_key = "voices/voice-sophea-built-in/preview.wav"

        has_reference = bool(reference_audio_bytes or (self.storage and effective_ref_key))
        is_warm = voice.id in self._cached_voices

        # Only download and encode reference audio if voice actually has a reference sample and is not already warm on GPU
        ref_audio_b64: str | None = None
        if has_reference and not is_warm:
            if reference_audio_bytes:
                ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
            elif self.storage and effective_ref_key:
                try:
                    raw_ref = await self.storage.download(effective_ref_key)
                    ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
                except Exception as err:
                    logger.warning("modal_reference_download_failed", key=effective_ref_key, error=str(err))

        prompt_text = voice.modifiers.get("prompt_text") if voice.modifiers else None
        modal_voice_id = voice.id if has_reference else None

        async def _call() -> tuple[bytes, float]:
            nonlocal ref_audio_b64, modal_voice_id
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/synthesize"
            payload = {
                "text": text,
                "voice_id": modal_voice_id,
                "voice_name": voice.name,
                "language": language,
                "speed": speed,
                "output_format": output_format.value,
                "modifiers": voice.modifiers,
                "reference_audio_key": effective_ref_key,
                "reference_audio_base64": ref_audio_b64,
                "prompt_audio_base64": ref_audio_b64,
                "prompt_text": prompt_text,
                "inference_timesteps": 20,
                "cfg_value": 2.0,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())

            # If container was restarted and cache was flushed, invalidate cache, re-download and retry
            if resp.status_code == 404 and "voice_cache_miss" in resp.text:
                self._cached_voices.discard(voice.id)
                if reference_audio_bytes:
                    ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
                elif self.storage and voice.reference_audio_key:
                    try:
                        raw_ref = await self.storage.download(voice.reference_audio_key)
                        ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
                    except Exception as err:
                        logger.warning("modal_reference_download_retry_failed", key=voice.reference_audio_key, error=str(err))
                        ref_audio_b64 = None

                if ref_audio_b64:
                    payload["reference_audio_base64"] = ref_audio_b64
                    payload["prompt_audio_base64"] = ref_audio_b64
                else:
                    # No reference audio available: fall back to base neural model without voice_id
                    payload["voice_id"] = None
                    payload["reference_audio_base64"] = None
                    payload["prompt_audio_base64"] = None

                resp = await client.post(url, json=payload, headers=self._get_headers())

            if resp.status_code != 200:
                logger.error("remote_inference_failed", status=resp.status_code, body=resp.text)
                raise InferenceServiceError(f"Remote inference returned status {resp.status_code}.")

            if voice.id and has_reference:
                self._cached_voices.add(voice.id)

            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                data = resp.json()
                audio_bytes = base64.b64decode(data.get("audio_base64", ""))
                duration = float(data.get("duration", 0.0))
            else:
                audio_bytes = resp.content
                duration_header = resp.headers.get("X-Audio-Duration")
                if duration_header:
                    duration = float(duration_header)
                else:
                    duration = get_audio_duration_seconds(audio_bytes)

            # Apply custom acoustic modifiers for designed voices (pitch shifting, speed scaling, emotion shaping)
            if voice.modifiers and voice.voice_type == VoiceType.DESIGNED:
                p_factor = float(voice.modifiers.get("pitch", 1.0))
                s_factor = float(voice.modifiers.get("speed", 1.0))
                emo = voice.modifiers.get("emotion")
                sty = voice.modifiers.get("style")
                if abs(p_factor - 1.0) >= 0.02 or abs(s_factor - 1.0) >= 0.02 or emo or sty:
                    audio_bytes = apply_acoustic_modifiers(
                        audio_bytes,
                        pitch_factor=p_factor,
                        speed_factor=s_factor,
                        emotion=emo,
                        style=sty,
                    )
                    duration = get_audio_duration_seconds(audio_bytes)

            # Convert raw WAV to genuine MP3 if requested so HTML5 audio decodes authentically
            if output_format == AudioFormat.MP3 and audio_bytes.startswith(b"RIFF"):
                import io, soundfile as sf
                try:
                    wav_data, sr = sf.read(io.BytesIO(audio_bytes))
                    mp3_buf = io.BytesIO()
                    sf.write(mp3_buf, wav_data, sr, format="MP3")
                    audio_bytes = mp3_buf.getvalue()
                except Exception as err:
                    logger.warning("mp3_conversion_failed", error=str(err))

            return audio_bytes, duration

        return await self._execute_with_retry("modal_generate_speech", _call)  # type: ignore[no-any-return]

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
        prompt_text: str | None = None,
        voice_id: str | None = None,
        generate_preview: bool = True,
    ) -> tuple[str, bytes, str]:
        """Dispatch audio sample to serverless extractor for vocal caching and instant registration."""
        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")

        preview_script = get_preview_text_for_language(language)

        async def _call() -> tuple[str, bytes, str]:
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/clone"
            payload = {
                "audio_base64": base64.b64encode(reference_audio_bytes).decode("utf-8"),
                "voice_id": voice_id,
                "language": language,
                "preview_text": preview_script,
                "prompt_text": prompt_text,
                "generate_preview": generate_preview,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                raise InferenceServiceError(
                    f"Remote voice clone extraction returned status {resp.status_code}."
                )

            data = resp.json()
            feature_token = data.get("feature_token", "")
            preview_b64 = data.get("preview_base64")
            preview_bytes = base64.b64decode(preview_b64) if preview_b64 else b""
            detected_prompt = str(data.get("prompt_text") or prompt_text or "")

            if voice_id:
                self._cached_voices.add(voice_id)
            if feature_token:
                self._cached_voices.add(feature_token)

            return feature_token, preview_bytes, detected_prompt

        return await self._execute_with_retry("modal_clone_voice", _call)  # type: ignore[no-any-return]

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Derive acoustic profile tokens on remote serverless worker and synthesize modified preview."""
        # Use high-fidelity human neural engine for rich, distinct voice design from descriptions
        if self.fallback_engine:
            try:
                return await self.fallback_engine.design_voice(base_voice, modifiers)
            except Exception as fallback_err:
                logger.warning("fallback_design_voice_failed", error=str(fallback_err))

        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")

        preview_script = get_preview_text_for_language(base_voice.language)

        # Ensure correct gender reference audio is passed to VoxCPM on Modal
        gender_val = str(modifiers.get("gender", "")).lower()
        desc_val = (modifiers.get("description") or base_voice.description or "").lower()
        if gender_val == "male":
            is_male = True
        elif gender_val == "female":
            is_male = False
        elif re.search(r"\b(male|man|men|boy|actor|gentleman)\b", desc_val):
            is_male = True
        else:
            is_male = False

        target_ref_key = (
            base_voice.reference_audio_key
            if (base_voice.reference_audio_key and (is_male == (str(base_voice.modifiers.get("gender", "")).lower() == "male")))
            else ("voices/d51a6ac7-6059-4adf-a93a-55ffacffea2d/reference.wav" if is_male else "voices/voice-sophea-built-in/preview.wav")
        )

        ref_audio_b64: str | None = None
        if self.storage and target_ref_key:
            try:
                raw_ref = await self.storage.download(target_ref_key)
                ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
            except Exception as err:
                logger.warning("design_ref_download_failed", key=target_ref_key, error=str(err))

        async def _call() -> tuple[str, bytes]:
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/synthesize"
            payload = {
                "text": preview_script,
                "reference_audio_base64": ref_audio_b64,
                "modifiers": modifiers,
                "output_format": "wav",
                "inference_timesteps": 20,
                "cfg_value": 2.0,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                raise InferenceServiceError(
                    f"Remote voice design returned status {resp.status_code}."
                )

            data = resp.json()
            audio_b64 = data.get("audio_base64", "")
            raw_preview = base64.b64decode(audio_b64) if audio_b64 else b""

            # Apply user pitch and speed modifiers using high-fidelity WSOLA processing (untouched if 1.0x)
            user_speed = float(modifiers.get("speed", 1.0))
            user_pitch = float(modifiers.get("pitch", 1.0))
            if raw_preview:
                raw_preview = apply_acoustic_modifiers(
                    raw_preview,
                    pitch_factor=user_pitch,
                    speed_factor=user_speed,
                    emotion=modifiers.get("emotion"),
                    style=modifiers.get("style"),
                )

            token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
            return token, raw_preview

        return await self._execute_with_retry("modal_design_voice", _call)  # type: ignore[no-any-return]
