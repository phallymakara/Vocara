"""Modal / Serverless VoxCPM 2 inference engine adapter."""

import base64
import re
import uuid
from typing import Any

import httpx
import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.constants import get_preview_text_for_language
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, VoiceType
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import apply_acoustic_modifiers, get_audio_duration_seconds

logger = structlog.get_logger("vocara.inference.modal")


class ModalInferenceEngine(BaseInferenceEngine):
    """Adapter for remote serverless VoxCPM 2 GPU execution."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int = 120,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
        storage: BlobStorage | None = None,
        inference_timesteps: int = 20,
        cfg_value: float = 2.0,
        max_chunk_chars: int = 180,
        default_km_preview: str | None = None,
        default_en_preview: str | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, max_retries=max_retries)
        self.endpoint_url = endpoint_url
        self.api_token = api_token
        self._client = http_client
        self.storage = storage
        self.inference_timesteps = inference_timesteps
        self.cfg_value = cfg_value
        self.max_chunk_chars = max_chunk_chars
        self.default_km_preview = default_km_preview
        self.default_en_preview = default_en_preview
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

    @staticmethod
    def distill_voice_instruction(
        modifiers: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> str:
        """Condense user descriptions into concise ASCII VoxCPM 2 cues (prevents speaking prompt text aloud)."""
        mods = modifiers or {}
        explicit = str(mods.get("control_instruction") or "").strip().strip("()")
        if explicit:
            ascii_explicit = re.sub(r"[^\x20-\x7E]+", " ", explicit)
            return re.sub(r"\s+", " ", ascii_explicit)[:140].strip()

        cues: list[str] = []
        gender = str(mods.get("gender") or "").strip().lower()
        if gender == "female":
            cues.append("woman")
        elif gender == "male":
            cues.append("man")

        raw_desc = str(mods.get("description") or description or "").strip()
        if raw_desc:
            first_clause = re.split(r"[\n.!?។]+", raw_desc)[0].strip()
            ascii_clause = re.sub(r"[^\x20-\x7E]+", " ", first_clause).strip()
            if ascii_clause:
                cues.append(ascii_clause[:90].strip())

        emotion = str(mods.get("emotion") or "").strip()
        if emotion:
            ascii_emo = re.sub(r"[^\x20-\x7E]+", " ", emotion).strip()
            if ascii_emo:
                cues.append(f"{ascii_emo} tone")

        style = str(mods.get("style") or "").strip()
        if style:
            ascii_sty = re.sub(r"[^\x20-\x7E]+", " ", style).strip()
            if ascii_sty:
                cues.append(f"{ascii_sty} style")

        try:
            pitch = float(mods.get("pitch", 1.0))
            if pitch <= 0.85:
                cues.append("deep lower pitch")
            elif pitch >= 1.15:
                cues.append("bright higher pitch")
        except (TypeError, ValueError):
            pass

        try:
            speed = float(mods.get("speed", 1.0))
            if speed <= 0.85:
                cues.append("speaks slowly")
            elif speed >= 1.15:
                cues.append("lively pace")
        except (TypeError, ValueError):
            pass

        combined = ", ".join(cues)
        return re.sub(r"\s+", " ", combined)[:140].strip()

    def _resolve_preview_script(self, language: str | None, custom_text: str | None = None) -> str:
        if custom_text and custom_text.strip():
            return custom_text.strip()
        return get_preview_text_for_language(
            language,
            km_default=self.default_km_preview,
            en_default=self.default_en_preview,
        )

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Call remote serverless VoxCPM 2 worker to synthesize speech."""
        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")
        endpoint_base = self.endpoint_url.rstrip("/")

        if voice.voice_type == VoiceType.DESIGNED:
            # Prefer a designed voice's own synthesized preview WAV over a parent/base fallback key
            effective_ref_key = (
                voice.preview_audio_key
                if voice.preview_audio_key and voice.id in voice.preview_audio_key
                else (voice.reference_audio_key or voice.preview_audio_key)
            )
        else:
            effective_ref_key = voice.reference_audio_key or voice.preview_audio_key

        has_reference = bool(reference_audio_bytes or (self.storage and effective_ref_key))
        is_warm = voice.id in self._cached_voices

        ref_audio_b64: str | None = None
        if has_reference and not is_warm:
            if reference_audio_bytes:
                ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
            elif self.storage and effective_ref_key:
                try:
                    raw_ref = await self.storage.download(effective_ref_key)
                    ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
                except Exception as err:
                    logger.warning(
                        "modal_reference_download_failed",
                        key=effective_ref_key,
                        error=str(err),
                    )
                    has_reference = False

        modifiers = voice.modifiers or {}
        # Keep pure isolated reference timbre whenever reference audio is present; only apply
        # control_instruction if synthesizing without reference audio.
        prompt_text = None
        control_instruction = (
            "" if has_reference else self.distill_voice_instruction(modifiers, voice.description)
        )
        modal_voice_id = voice.id if has_reference else None

        async def _call() -> tuple[bytes, float]:
            nonlocal ref_audio_b64, modal_voice_id
            client = await self._get_client()
            url = f"{endpoint_base}/synthesize"
            payload = {
                "text": text,
                "voice_id": modal_voice_id,
                "voice_name": voice.name,
                "voice_type": voice.voice_type.value,
                "language": language,
                "speed": speed,
                "output_format": output_format.value,
                "modifiers": modifiers,
                "control_instruction": control_instruction or None,
                "reference_audio_key": effective_ref_key,
                "reference_audio_base64": ref_audio_b64,
                "prompt_audio_base64": ref_audio_b64,
                "prompt_text": prompt_text,
                "inference_timesteps": self.inference_timesteps,
                "cfg_value": self.cfg_value,
                "max_chunk_chars": self.max_chunk_chars,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())

            # If container restarted and cache cleared, re-download reference audio and retry
            if resp.status_code == 404 and "voice_cache_miss" in resp.text:
                self._cached_voices.discard(voice.id)
                if reference_audio_bytes:
                    ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
                elif self.storage and effective_ref_key:
                    try:
                        raw_ref = await self.storage.download(effective_ref_key)
                        ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
                    except Exception as err:
                        logger.warning(
                            "modal_reference_download_retry_failed",
                            key=effective_ref_key,
                            error=str(err),
                        )
                        ref_audio_b64 = None

                if ref_audio_b64:
                    payload["reference_audio_base64"] = ref_audio_b64
                    payload["prompt_audio_base64"] = ref_audio_b64
                else:
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
                duration = (
                    float(duration_header)
                    if duration_header
                    else get_audio_duration_seconds(audio_bytes)
                )

            # Apply explicit TTS request playback speed adjustment without altering speaker pitch/timbre
            if abs(speed - 1.0) >= 0.05:
                audio_bytes = apply_acoustic_modifiers(
                    audio_bytes,
                    pitch_factor=1.0,
                    speed_factor=speed,
                )
                duration = get_audio_duration_seconds(audio_bytes)

            if output_format == AudioFormat.MP3 and audio_bytes.startswith(b"RIFF"):
                import io
                import soundfile as sf

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
        endpoint_base = self.endpoint_url.rstrip("/")

        preview_script = self._resolve_preview_script(language)

        async def _call() -> tuple[str, bytes, str]:
            client = await self._get_client()
            url = f"{endpoint_base}/clone"
            payload = {
                "audio_base64": base64.b64encode(reference_audio_bytes).decode("utf-8"),
                "voice_id": voice_id,
                "language": language,
                "preview_text": preview_script,
                "prompt_text": prompt_text,
                "generate_preview": generate_preview,
                "inference_timesteps": self.inference_timesteps,
                "cfg_value": self.cfg_value,
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

    async def preview_designed_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
        preview_text: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize a VoxCPM 2 voice design preview anchored to the primary Khmer base speaker when available."""
        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")
        endpoint_base = self.endpoint_url.rstrip("/")

        target_script = self._resolve_preview_script(base_voice.language, preview_text)
        instruction = self.distill_voice_instruction(modifiers, modifiers.get("description") or base_voice.description)

        # Anchor Khmer voice design to the selected Khmer base voice sample so accent stays native Cambodian
        base_ref_key = base_voice.reference_audio_key or base_voice.preview_audio_key
        ref_audio_b64: str | None = None
        if self.storage and base_ref_key:
            try:
                raw_ref = await self.storage.download(base_ref_key)
                ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
            except Exception as err:
                logger.warning("design_base_ref_download_failed", key=base_ref_key, error=str(err))

        async def _call() -> dict[str, Any]:
            client = await self._get_client()
            url = f"{endpoint_base}/design"
            payload: dict[str, Any] = {
                "base_voice_id": base_voice.id,
                "modifiers": modifiers,
                "control_instruction": instruction or None,
                "preview_text": target_script,
                "inference_timesteps": self.inference_timesteps,
                "cfg_value": self.cfg_value,
            }
            if ref_audio_b64:
                payload["reference_audio_base64"] = ref_audio_b64

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                raise InferenceServiceError(
                    f"Remote voice design returned status {resp.status_code}."
                )

            data = resp.json()
            audio_b64 = data.get("audio_base64") or data.get("preview_base64") or ""
            raw_preview = base64.b64decode(audio_b64) if audio_b64 else b""
            duration = float(data.get("duration") or (get_audio_duration_seconds(raw_preview) if raw_preview else 0.0))

            return {
                "feature_token": data.get("feature_token") or f"voxcpm_des_{uuid.uuid4().hex[:12]}",
                "audio_bytes": raw_preview,
                "duration": duration,
                "control_instruction": data.get("control_instruction") or instruction,
                "prompt_text": data.get("prompt_text") or target_script,
            }

        return await self._execute_with_retry("modal_design_voice", _call)  # type: ignore[no-any-return]

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
        preview_text: str | None = None,
    ) -> tuple[str, bytes]:
        """Design a new voice identity on Modal VoxCPM 2 from acoustic descriptions."""
        res = await self.preview_designed_voice(
            base_voice=base_voice,
            modifiers=modifiers,
            preview_text=preview_text,
        )
        if res.get("control_instruction"):
            modifiers["control_instruction"] = res["control_instruction"]
        if res.get("prompt_text"):
            modifiers["prompt_text"] = res["prompt_text"]
        return str(res["feature_token"]), bytes(res["audio_bytes"])
