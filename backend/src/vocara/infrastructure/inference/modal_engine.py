"""Modal / Serverless VoxCPM inference engine adapter."""

import base64
from typing import Any

import httpx
import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.constants import DEFAULT_PREVIEW_TEXT
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, VoiceType
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import get_audio_duration_seconds

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

        # Download reference audio if voice is cloned
        ref_audio_b64: str | None = None
        if reference_audio_bytes:
            ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
        elif self.storage and voice.reference_audio_key:
            try:
                raw_ref = await self.storage.download(voice.reference_audio_key)
                ref_audio_b64 = base64.b64encode(raw_ref).decode("utf-8")
            except Exception as err:
                logger.warning("modal_reference_download_failed", key=voice.reference_audio_key, error=str(err))

        prompt_text = voice.modifiers.get("prompt_text") if voice.modifiers else None

        async def _call() -> tuple[bytes, float]:
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/synthesize"
            payload = {
                "text": text,
                "voice_id": voice.id,
                "voice_name": voice.name,
                "language": language,
                "speed": speed,
                "output_format": output_format.value,
                "modifiers": voice.modifiers,
                "reference_audio_key": voice.reference_audio_key,
                "reference_audio_base64": ref_audio_b64,
                "prompt_audio_base64": ref_audio_b64,
                "prompt_text": prompt_text,
                "inference_timesteps": 20,
                "cfg_value": 2.0,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                logger.error("remote_inference_failed", status=resp.status_code, body=resp.text)
                raise InferenceServiceError(f"Remote inference returned status {resp.status_code}.")

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

            return audio_bytes, duration

        return await self._execute_with_retry("modal_generate_speech", _call)  # type: ignore[no-any-return]

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
        prompt_text: str | None = None,
    ) -> tuple[str, bytes, str]:
        """Dispatch audio sample to serverless extractor for vocal embeddings and transcription."""
        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")

        async def _call() -> tuple[str, bytes, str]:
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/clone"
            payload = {
                "audio_base64": base64.b64encode(reference_audio_bytes).decode("utf-8"),
                "language": language,
                "preview_text": DEFAULT_PREVIEW_TEXT,
                "prompt_text": prompt_text,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                raise InferenceServiceError(
                    f"Remote voice clone extraction returned status {resp.status_code}."
                )

            data = resp.json()
            feature_token = data.get("feature_token", "")
            preview_b64 = data.get("preview_base64")
            preview_bytes = base64.b64decode(preview_b64) if preview_b64 else reference_audio_bytes
            detected_prompt = str(data.get("prompt_text") or prompt_text or "")
            return feature_token, preview_bytes, detected_prompt

        return await self._execute_with_retry("modal_clone_voice", _call)  # type: ignore[no-any-return]

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Derive acoustic profile tokens on remote serverless worker."""
        if not self.endpoint_url:
            raise InferenceServiceError("Modal inference endpoint URL is not configured.")

        async def _call() -> tuple[str, bytes]:
            client = await self._get_client()
            url = f"{self.endpoint_url.rstrip('/')}/design"
            payload = {
                "base_voice_id": base_voice.id,
                "modifiers": modifiers,
                "preview_text": DEFAULT_PREVIEW_TEXT,
            }

            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code != 200:
                raise InferenceServiceError(
                    f"Remote voice design returned status {resp.status_code}."
                )

            data = resp.json()
            feature_token = data.get("feature_token", "")
            preview_b64 = data.get("preview_base64")
            preview_bytes = base64.b64decode(preview_b64) if preview_b64 else b""
            return feature_token, preview_bytes

        return await self._execute_with_retry("modal_design_voice", _call)  # type: ignore[no-any-return]
