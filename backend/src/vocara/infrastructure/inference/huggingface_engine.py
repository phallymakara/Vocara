"""Hugging Face Inference Endpoint and Gradio Space adapter for VoxCPM."""

import base64
import json
import uuid
from typing import Any

import httpx
import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.constants import DEFAULT_PREVIEW_TEXT
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat
from vocara.domain.ports import BlobStorage
from vocara.infrastructure.inference.base import BaseInferenceEngine
from vocara.utils.audio import get_audio_duration_seconds

logger = structlog.get_logger("vocara.inference.huggingface")

BACKUP_REPLICA_SPACE = "https://Kansasfan-voxcpm2-zerogpu-backend.hf.space"


class HuggingFaceInferenceEngine(BaseInferenceEngine):
    """Adapter for remote VoxCPM execution on Hugging Face Spaces or Inference Endpoints."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_token: str | None = None,
        model_id: str = "openbmb/VoxCPM2",
        timeout_seconds: int = 120,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
        storage: BlobStorage | None = None,
        fallback_engine: BaseInferenceEngine | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, max_retries=max_retries)
        self.endpoint_url = endpoint_url
        self.api_token = api_token
        self.model_id = model_id
        self._client = http_client
        self.storage = storage
        self.fallback_engine = fallback_engine

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _is_gradio_space(self, url: str) -> bool:
        """Determine whether endpoint points to a Gradio Hugging Face Space."""
        if not url:
            return False
        clean = url.lower()
        return ".hf.space" in clean or "/spaces/" in clean

    async def _gradio_generate(
        self,
        client: httpx.AsyncClient,
        clean_url: str,
        text: str,
        voice: Voice | None = None,
        ref_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Execute speech generation through Gradio 5 SSE queue flow on Hugging Face Space."""
        uploaded_file_path: str | None = None

        # 1. Upload reference audio file to Gradio if reference sample is provided
        auth_headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        if ref_audio_bytes:
            upload_url = f"{clean_url}/gradio_api/upload"
            try:
                upload_resp = await client.post(
                    upload_url,
                    files={"files": ("reference.wav", ref_audio_bytes, "audio/wav")},
                    headers=auth_headers,
                    timeout=self.timeout_seconds,
                )
                if upload_resp.status_code == 200:
                    file_list = upload_resp.json()
                    if isinstance(file_list, list) and len(file_list) > 0:
                        uploaded_file_path = file_list[0]
                else:
                    logger.warning(
                        "hf_gradio_upload_failed",
                        status=upload_resp.status_code,
                        body=upload_resp.text[:150],
                    )
            except Exception as upload_err:
                logger.warning("hf_gradio_upload_exception", error=str(upload_err))

        prompt_file_data = (
            {"path": uploaded_file_path, "meta": {"_type": "gradio.FileData"}}
            if uploaded_file_path
            else None
        )

        voice_id = voice.id if voice else "default"
        gender = "Auto"
        if voice and voice.modifiers:
            g = str(voice.modifiers.get("gender", "")).capitalize()
            if g in ("Male", "Female"):
                gender = g

        # 2. Try VoxCPM2 /call/tts API first, fallback to /call/generate_speech
        call_url = f"{clean_url}/gradio_api/call/tts"
        endpoint_action = "tts"
        call_payload: dict[str, Any] = {
            "data": [
                text,
                voice_id,
                gender,
                prompt_file_data,
                1.8,
                8,
            ]
        }
        call_resp = await client.post(
            call_url,
            json=call_payload,
            headers=self._get_headers(),
            timeout=self.timeout_seconds,
        )

        # If 404 or unprocessable, fallback to older /generate_speech schema
        if call_resp.status_code in (404, 422):
            call_url = f"{clean_url}/gradio_api/call/generate_speech"
            endpoint_action = "generate_speech"
            call_payload = {
                "data": [
                    text,
                    prompt_file_data,
                    None,
                    2.0,
                    10,
                    False,
                    False,
                    True,
                    3,
                    6.0,
                ]
            }
            call_resp = await client.post(
                call_url,
                json=call_payload,
                headers=self._get_headers(),
                timeout=self.timeout_seconds,
            )

        if call_resp.status_code != 200:
            raise InferenceServiceError(
                f"Hugging Face Gradio call failed with status {call_resp.status_code}: {call_resp.text[:200]}"
            )

        call_data = call_resp.json()
        event_id = call_data.get("event_id")
        if not event_id:
            raise InferenceServiceError(f"Hugging Face Gradio response missing event_id: {call_data}")

        # 3. Stream SSE until completion
        stream_url = f"{clean_url}/gradio_api/call/{endpoint_action}/{event_id}"
        audio_url: str | None = None
        current_event: str | None = None

        async with client.stream(
            "GET", stream_url, headers=auth_headers, timeout=self.timeout_seconds
        ) as stream:
            async for raw_line in stream.aiter_lines():
                line = raw_line.strip()
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line.startswith("data:"):
                    payload_str = line[5:].strip()

                    # Handle explicit SSE error event with payload extraction
                    if current_event == "error":
                        error_detail = payload_str
                        try:
                            err_json = json.loads(payload_str)
                            if isinstance(err_json, dict) and "error" in err_json:
                                error_detail = err_json["error"]
                        except Exception:
                            pass
                        raise InferenceServiceError(f"Hugging Face ZeroGPU error: {error_detail}")

                    try:
                        data = json.loads(payload_str)
                        if isinstance(data, list) and len(data) > 0:
                            item = data[0]
                            if isinstance(item, dict):
                                audio_url = item.get("url")
                            elif isinstance(item, str) and item.startswith("http"):
                                audio_url = item
                        if audio_url:
                            break
                    except Exception:
                        continue

        if not audio_url:
            raise InferenceServiceError("No audio URL found in Hugging Face Gradio completion event")

        # 4. Fetch the generated audio file
        if not audio_url.startswith("http"):
            audio_url = f"{clean_url}{audio_url if audio_url.startswith('/') else '/' + audio_url}"

        audio_resp = await client.get(audio_url, headers=auth_headers, timeout=self.timeout_seconds)
        if audio_resp.status_code != 200:
            raise InferenceServiceError(
                f"Failed to download generated audio from Hugging Face Space: {audio_resp.status_code}"
            )

        audio_bytes = audio_resp.content
        duration = get_audio_duration_seconds(audio_bytes)
        return audio_bytes, duration

    async def generate_speech(
        self,
        text: str,
        voice: Voice,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        reference_audio_bytes: bytes | None = None,
    ) -> tuple[bytes, float]:
        """Synthesize speech using Hugging Face VoxCPM Inference Endpoint with fallback."""
        # 1. Fetch reference audio sample for cloned voices
        raw_ref_bytes: bytes | None = reference_audio_bytes
        ref_audio_b64: str | None = None
        if reference_audio_bytes:
            ref_audio_b64 = base64.b64encode(reference_audio_bytes).decode("utf-8")
        elif self.storage and voice.reference_audio_key:
            try:
                raw_ref_bytes = await self.storage.download(voice.reference_audio_key)
                ref_audio_b64 = base64.b64encode(raw_ref_bytes).decode("utf-8")
            except Exception as err:
                logger.warning(
                    "reference_audio_download_failed",
                    key=voice.reference_audio_key,
                    error=str(err),
                )

        # 2. Build VoxCPM prompt instruction format (e.g. `(description, pitch, speed) text`)
        voice_type_val = getattr(voice.voice_type, "value", str(voice.voice_type)).lower()
        instruction_cues: list[str] = []

        if voice.description:
            instruction_cues.append(voice.description)
        pitch_mod = voice.modifiers.get("pitch")
        if pitch_mod and float(pitch_mod) != 1.0:
            instruction_cues.append(f"pitch: {pitch_mod}x")
        voice_speed = float(voice.modifiers.get("speed", 1.0))
        effective_speed = round(speed * voice_speed, 2)
        if effective_speed != 1.0:
            instruction_cues.append(f"speed: {effective_speed}x")
        if voice.modifiers.get("emotion"):
            instruction_cues.append(f"emotion: {voice.modifiers['emotion']}")
        if voice.modifiers.get("style"):
            instruction_cues.append(f"style: {voice.modifiers['style']}")

        control_instruction = ", ".join(instruction_cues)
        voxcpm_prompt = f"({control_instruction}) {text}" if control_instruction else text

        clean_url = self.endpoint_url.rstrip("/") if self.endpoint_url else ""

        # If endpoint is configured, attempt remote call
        if clean_url:
            async def _call() -> tuple[bytes, float]:
                client = await self._get_client()

                # If Gradio Space (such as voxcpm2-zerogpu-backend), use Gradio queue flow
                if self._is_gradio_space(clean_url):
                    try:
                        return await self._gradio_generate(
                            client=client,
                            clean_url=clean_url,
                            text=text,
                            voice=voice,
                            ref_audio_bytes=raw_ref_bytes,
                        )
                    except Exception as primary_err:
                        if clean_url != BACKUP_REPLICA_SPACE:
                            logger.info(
                                "hf_trying_backup_space",
                                backup=BACKUP_REPLICA_SPACE,
                                primary_error=str(primary_err),
                            )
                            return await self._gradio_generate(
                                client=client,
                                clean_url=BACKUP_REPLICA_SPACE,
                                text=text,
                                voice=voice,
                                ref_audio_bytes=raw_ref_bytes,
                            )
                        raise

                # Standard Inference Router or dedicated endpoint
                if "api-inference.huggingface.co" in clean_url or "router.huggingface.co" in clean_url:
                    synthesize_url = clean_url
                elif clean_url.endswith("/synthesize"):
                    synthesize_url = clean_url
                elif "/endpoints.huggingface.cloud" in clean_url:
                    synthesize_url = f"{clean_url}/synthesize"
                else:
                    synthesize_url = clean_url

                payload = {
                    "inputs": voxcpm_prompt,
                    "text": voxcpm_prompt,
                    "raw_text": text,
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "voice_type": voice_type_val,
                    "language": language,
                    "speed": speed,
                    "output_format": output_format.value,
                    "modifiers": voice.modifiers,
                    "control_instruction": control_instruction,
                    "reference_audio_base64": ref_audio_b64,
                    "prompt_audio_base64": ref_audio_b64,
                    "reference_audio_key": voice.reference_audio_key,
                }

                resp = await client.post(synthesize_url, json=payload, headers=self._get_headers())
                if resp.status_code != 200:
                    logger.error("hf_voxcpm_inference_failed", status=resp.status_code, body=resp.text[:200])
                    raise InferenceServiceError(
                        f"Hugging Face inference returned status {resp.status_code}: {resp.text[:200]}"
                    )

                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = resp.json()
                    if isinstance(data, dict) and "audio_base64" in data:
                        audio_bytes = base64.b64decode(data["audio_base64"])
                    elif isinstance(data, dict) and "audio" in data:
                        audio_bytes = base64.b64decode(data["audio"])
                    elif isinstance(data, list) and len(data) > 0 and "audio" in data[0]:
                        audio_bytes = base64.b64decode(data[0]["audio"])
                    else:
                        audio_bytes = resp.content
                    duration = float(data.get("duration", 0.0)) if isinstance(data, dict) else 0.0
                else:
                    audio_bytes = resp.content
                    duration_header = resp.headers.get("X-Audio-Duration")
                    if duration_header:
                        duration = float(duration_header)
                    else:
                        duration = get_audio_duration_seconds(audio_bytes)

                if duration <= 0.0:
                    try:
                        duration = get_audio_duration_seconds(audio_bytes)
                    except Exception:
                        duration = max(0.5, len(text) / 15.0)

                return audio_bytes, duration

            try:
                return await self._execute_with_retry("hf_generate_speech", _call)
            except Exception as err:
                logger.warning(
                    "hf_voxcpm_remote_failed_falling_back",
                    endpoint=clean_url,
                    error=str(err),
                )
                if self.fallback_engine:
                    return await self.fallback_engine.generate_speech(
                        text=text,
                        voice=voice,
                        language=language,
                        speed=speed,
                        output_format=output_format,
                        reference_audio_bytes=reference_audio_bytes,
                    )
                raise

        # If endpoint is not configured, use acoustic fallback engine
        if self.fallback_engine:
            return await self.fallback_engine.generate_speech(
                text=text,
                voice=voice,
                language=language,
                speed=speed,
                output_format=output_format,
                reference_audio_bytes=reference_audio_bytes,
            )

        raise InferenceServiceError("Hugging Face inference endpoint URL is not configured.")

    async def clone_voice(
        self,
        reference_audio_bytes: bytes,
        language: str = "km-KH",
    ) -> tuple[str, bytes]:
        """Dispatch audio sample to Hugging Face endpoint for voice embedding extraction and preview synthesis."""
        clean_url = self.endpoint_url.rstrip("/") if self.endpoint_url else ""
        if clean_url:
            async def _call() -> tuple[str, bytes]:
                client = await self._get_client()

                # If Gradio Space, synthesize canonical preview using the reference voice
                if self._is_gradio_space(clean_url):
                    try:
                        audio_bytes, _ = await self._gradio_generate(
                            client=client,
                            clean_url=clean_url,
                            text=DEFAULT_PREVIEW_TEXT,
                            ref_audio_bytes=reference_audio_bytes,
                        )
                    except Exception as primary_err:
                        if clean_url != BACKUP_REPLICA_SPACE:
                            logger.info(
                                "hf_clone_trying_backup_space",
                                backup=BACKUP_REPLICA_SPACE,
                                primary_error=str(primary_err),
                            )
                            audio_bytes, _ = await self._gradio_generate(
                                client=client,
                                clean_url=BACKUP_REPLICA_SPACE,
                                text=DEFAULT_PREVIEW_TEXT,
                                ref_audio_bytes=reference_audio_bytes,
                            )
                        else:
                            raise
                    return f"hf_voxcpm_{uuid.uuid4().hex[:12]}", audio_bytes

                url = f"{clean_url}/clone"
                payload = {
                    "audio_base64": base64.b64encode(reference_audio_bytes).decode("utf-8"),
                    "language": language,
                    "preview_text": DEFAULT_PREVIEW_TEXT,
                }
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code != 200:
                    raise InferenceServiceError(
                        f"Hugging Face voice clone returned status {resp.status_code}."
                    )
                data = resp.json()
                feature_token = data.get("feature_token", "")
                preview_b64 = data.get("preview_base64")
                preview_bytes = (
                    base64.b64decode(preview_b64) if preview_b64 else reference_audio_bytes
                )
                return feature_token, preview_bytes

            try:
                return await self._execute_with_retry("hf_clone_voice", _call)
            except Exception as err:
                logger.warning("hf_voxcpm_clone_failed_falling_back", error=str(err))
                if self.fallback_engine:
                    return await self.fallback_engine.clone_voice(reference_audio_bytes, language=language)
                return f"emb_{uuid.uuid4().hex[:16]}", reference_audio_bytes

        if self.fallback_engine:
            return await self.fallback_engine.clone_voice(reference_audio_bytes, language=language)

        return f"emb_{uuid.uuid4().hex[:16]}", reference_audio_bytes

    async def design_voice(
        self,
        base_voice: Voice,
        modifiers: dict[str, Any],
    ) -> tuple[str, bytes]:
        """Derive acoustic profile tokens on remote Hugging Face endpoint."""
        clean_url = self.endpoint_url.rstrip("/") if self.endpoint_url else ""
        if clean_url:
            async def _call() -> tuple[str, bytes]:
                client = await self._get_client()

                if self._is_gradio_space(clean_url):
                    base_ref_bytes: bytes | None = None
                    if self.storage and base_voice.reference_audio_key:
                        try:
                            base_ref_bytes = await self.storage.download(base_voice.reference_audio_key)
                        except Exception:
                            pass
                    try:
                        preview_bytes, _ = await self._gradio_generate(
                            client=client,
                            clean_url=clean_url,
                            text=DEFAULT_PREVIEW_TEXT,
                            voice=base_voice,
                            ref_audio_bytes=base_ref_bytes,
                        )
                    except Exception as primary_err:
                        if clean_url != BACKUP_REPLICA_SPACE:
                            preview_bytes, _ = await self._gradio_generate(
                                client=client,
                                clean_url=BACKUP_REPLICA_SPACE,
                                text=DEFAULT_PREVIEW_TEXT,
                                voice=base_voice,
                                ref_audio_bytes=base_ref_bytes,
                            )
                        else:
                            raise
                    return f"hf_voxcpm_des_{uuid.uuid4().hex[:12]}", preview_bytes

                url = f"{clean_url}/design"
                payload = {
                    "base_voice_id": base_voice.id,
                    "modifiers": modifiers,
                    "preview_text": DEFAULT_PREVIEW_TEXT,
                }
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code != 200:
                    raise InferenceServiceError(
                        f"Hugging Face voice design returned status {resp.status_code}."
                    )
                data = resp.json()
                feature_token = data.get("feature_token", "")
                preview_b64 = data.get("preview_base64")
                preview_bytes = base64.b64decode(preview_b64) if preview_b64 else b""
                return feature_token, preview_bytes

            try:
                return await self._execute_with_retry("hf_design_voice", _call)
            except Exception as err:
                logger.warning("hf_voxcpm_design_failed_falling_back", error=str(err))
                if self.fallback_engine:
                    return await self.fallback_engine.design_voice(base_voice, modifiers)
                return f"emb_var_{uuid.uuid4().hex[:16]}", b""

        if self.fallback_engine:
            return await self.fallback_engine.design_voice(base_voice, modifiers)

        return f"emb_var_{uuid.uuid4().hex[:16]}", b""
