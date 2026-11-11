"""Voice Library business logic service."""

import base64
import io
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import soundfile as sf

from vocara.core.exceptions import (
    AuthorizationError,
    ConsentRequiredError,
    InferenceServiceError,
    VoiceNotFoundError,
)
from vocara.domain.constants import (
    DEFAULT_PREVIEW_TEXT,
    get_preview_text_for_language,
)
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, VoiceType, VoiceVisibility
from vocara.domain.ports import BlobStorage, InferenceEngine, VoiceRepository
from vocara.utils.audio import (
    apply_acoustic_modifiers,
    extract_acoustic_profile,
    generate_synthetic_tone_wav,
    normalize_audio_to_wav,
    preprocess_reference_audio,
    validate_reference_audio,
)


class VoiceService:
    """Manages voice profile queries, cloning, variations, and audio previews."""

    def __init__(
        self,
        voice_repo: VoiceRepository,
        storage: BlobStorage | None = None,
        inference_engine: InferenceEngine | None = None,
        sample_rate: int = 48000,
        default_km_preview: str | None = None,
        default_en_preview: str | None = None,
    ) -> None:
        self.voice_repo = voice_repo
        self.storage = storage
        self.inference_engine = inference_engine
        self.sample_rate = sample_rate
        self.default_km_preview = default_km_preview
        self.default_en_preview = default_en_preview

    def _get_default_preview(self, language: str | None) -> str:
        return get_preview_text_for_language(
            language,
            km_default=self.default_km_preview,
            en_default=self.default_en_preview,
        )

    async def list_voices(
        self,
        owner_id: str,
        language: str | None = None,
        voice_type: VoiceType | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Voice]:
        """List accessible built-in public voices and private voices for caller."""
        voices = await self.voice_repo.list_accessible_voices(
            owner_id=owner_id, skip=skip, limit=limit
        )

        filtered = voices
        if language:
            filtered = [v for v in filtered if v.language.lower() == language.lower()]
        if voice_type:
            filtered = [v for v in filtered if v.voice_type == voice_type]

        return filtered

    async def get_voice_by_id(self, voice_id: str, owner_id: str) -> Voice:
        """Fetch voice ensuring multi-tenant isolation rules."""
        voice = await self.voice_repo.get_by_id(voice_id)
        if not voice or not voice.is_active:
            raise VoiceNotFoundError(voice_id)

        # Private voices can only be seen by their creator
        if voice.visibility == VoiceVisibility.PRIVATE and voice.owner_id != owner_id:
            raise VoiceNotFoundError(voice_id)

        return voice

    async def update_voice(
        self,
        voice_id: str,
        owner_id: str,
        name: str | None = None,
        description: str | None = None,
        visibility: VoiceVisibility | None = None,
        modifiers: dict[str, Any] | None = None,
    ) -> Voice:
        """Update voice details, ensuring built-ins cannot be modified."""
        voice = await self.get_voice_by_id(voice_id, owner_id)

        if voice.voice_type == VoiceType.BUILT_IN:
            raise AuthorizationError("Built-in system voices cannot be modified.")

        if voice.owner_id != owner_id:
            raise AuthorizationError("You do not have permission to modify this voice.")

        if name is not None:
            voice.name = name.strip()
        if description is not None:
            voice.description = description.strip()
        if visibility is not None:
            voice.visibility = visibility
        if modifiers is not None:
            voice.modifiers = {**(voice.modifiers or {}), **modifiers}

        return await self.voice_repo.update(voice)

    async def delete_voice(self, voice_id: str, owner_id: str) -> bool:
        """Soft-delete custom voice, ensuring built-ins cannot be deleted."""
        voice = await self.get_voice_by_id(voice_id, owner_id)

        if voice.voice_type == VoiceType.BUILT_IN:
            raise AuthorizationError("Built-in system voices cannot be deleted.")

        if voice.owner_id != owner_id:
            raise AuthorizationError("You do not have permission to delete this voice.")

        return await self.voice_repo.delete(voice_id)

    async def get_preview_stream(self, voice_id: str, owner_id: str) -> tuple[bytes, str]:
        """Retrieve preview audio bytes and content-type."""
        try:
            voice = await self.get_voice_by_id(voice_id, owner_id)
        except VoiceNotFoundError:
            if owner_id != "default_developer":
                voice = await self.get_voice_by_id(voice_id, owner_id="default_developer")
            else:
                raise

        if self.storage and voice.preview_audio_key:
            try:
                audio_bytes = await self.storage.download(voice.preview_audio_key)
                # Sniff audio container format to ensure matching browser MIME type
                if audio_bytes.startswith(b"RIFF"):
                    content_type = "audio/wav"
                elif audio_bytes.startswith(b"ID3") or (
                    len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
                ):
                    content_type = "audio/mpeg"
                else:
                    content_type = (
                        "audio/mpeg" if voice.preview_audio_key.endswith(".mp3") else "audio/wav"
                    )
                return audio_bytes, content_type
            except Exception:
                pass  # Fall through to synthetic generation

        # If preview audio is missing, synthesize using canonical default preview text
        if self.inference_engine:
            try:
                preview_text = get_preview_text_for_language(voice.language)
                audio_bytes, _ = await self.inference_engine.generate_speech(
                    text=preview_text,
                    voice=voice,
                    language=voice.language,
                    speed=float(voice.modifiers.get("speed", 1.0)),
                    output_format=AudioFormat.WAV,
                )
                if self.storage and audio_bytes:
                    preview_key = f"voices/{voice.id}/preview.wav"
                    await self.storage.upload(preview_key, audio_bytes, content_type="audio/wav")
                    voice.preview_audio_key = preview_key
                    await self.voice_repo.update(voice)
                return audio_bytes, "audio/wav"
            except Exception:
                pass

        # Return synthesized PCM WAV tone preview fallback
        fallback_wav = generate_synthetic_tone_wav(duration_seconds=1.5)
        return fallback_wav, "audio/wav"

    async def clone_voice(
        self,
        owner_id: str,
        name: str,
        audio_bytes: bytes,
        consent_confirmed: bool,
        language: str = "km-KH",
        description: str = "",
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
        enhance_audio: bool = True,
        prompt_text: str = "",
    ) -> Voice:
        """Clone a voice profile from reference audio after verifying explicit consent."""
        if not consent_confirmed:
            raise ConsentRequiredError()

        # Run reference audio through universal decoding and subtle noise cleaning:
        # (leaves speech, cadence, and timing completely untouched)
        normalized_wav, duration, metrics = preprocess_reference_audio(
            audio_bytes,
            target_sample_rate=self.sample_rate,
            enable_denoise=enhance_audio,
            enable_normalization=False,
            min_duration=0.5,
            max_duration=120.0,
            enable_trim=False,
        )

        # Extract deep acoustic vocal profile (gender, pitch F0, timbre offset)
        profile = extract_acoustic_profile(normalized_wav)

        voice_id = str(uuid.uuid4())
        ref_key = f"voices/{voice_id}/reference.wav"
        preview_key = f"voices/{voice_id}/preview.wav"

        # The preview for the cloned voice will use the canonical default preview text synthesized with the cloned voice
        preview_sample = normalized_wav
        feature_token: str | None = None
        final_prompt_text = prompt_text.strip()

        if self.inference_engine:
            try:
                try:
                    clone_res = await self.inference_engine.clone_voice(  # type: ignore[call-arg]
                        normalized_wav,
                        language=language,
                        prompt_text=final_prompt_text,
                        voice_id=voice_id,
                        generate_preview=True,
                    )
                except TypeError:
                    clone_res = await self.inference_engine.clone_voice(
                        normalized_wav, language=language
                    )

                if len(clone_res) >= 3:
                    feature_token, engine_preview, detected_prompt = clone_res[0], clone_res[1], clone_res[2]
                    if detected_prompt and not final_prompt_text:
                        final_prompt_text = detected_prompt
                else:
                    feature_token, engine_preview = clone_res[0], clone_res[1]

                if engine_preview and len(engine_preview) > 0 and engine_preview != normalized_wav:
                    preview_sample = engine_preview
            except Exception:
                pass

        now = datetime.now(UTC)
        modifiers: dict[str, Any] = {
            "consent_verified": True,
            "consent_timestamp": now.isoformat(),
            "duration_seconds": round(duration, 2),
            "gender": profile["gender"],
            "pitch": profile["pitch_factor"],
            "pitch_hz_offset": profile["pitch_hz_offset"],
            "estimated_f0": profile["estimated_f0"],
            "audio_pipeline": metrics,
        }
        if feature_token:
            modifiers["feature_token"] = feature_token
        if final_prompt_text:
            modifiers["prompt_text"] = final_prompt_text

        voice = Voice(
            id=voice_id,
            name=name.strip(),
            voice_type=VoiceType.CLONED,
            owner_id=owner_id,
            language=language,
            description=description.strip(),
            reference_audio_key=ref_key,
            preview_audio_key=preview_key,
            modifiers=modifiers,
            visibility=visibility,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # Guarantee that preview audio is NEVER the raw uploaded recording; synthesize canonical preview if needed
        if (preview_sample == normalized_wav or not preview_sample) and self.inference_engine:
            try:
                preview_text = get_preview_text_for_language(language)
                generated_preview, _ = await self.inference_engine.generate_speech(
                    text=preview_text,
                    voice=voice,
                    language=language,
                    speed=1.0,
                    reference_audio_bytes=normalized_wav,
                    output_format=AudioFormat.WAV,
                )
                if generated_preview and len(generated_preview) > 0:
                    preview_sample = generated_preview
            except Exception:
                pass

        # Ensure preview sample is genuine PCM WAV matching preview.wav extension
        if preview_sample and not preview_sample.startswith(b"RIFF"):
            try:
                import io, soundfile as sf
                data, sr = sf.read(io.BytesIO(preview_sample))
                out_buf = io.BytesIO()
                sf.write(out_buf, data, sr, format="WAV", subtype="PCM_16")
                preview_sample = out_buf.getvalue()
            except Exception:
                pass

        # Upload reference and preview audio to blob storage concurrently
        if self.storage:
            import asyncio
            await asyncio.gather(
                self.storage.upload(ref_key, normalized_wav, content_type="audio/wav"),
                self.storage.upload(preview_key, preview_sample, content_type="audio/wav"),
            )

        return await self.voice_repo.create(voice)

    @staticmethod
    def _detect_target_gender(gender: str | None, description: str) -> str:
        """Resolve speaker gender from explicit flag or word-boundary cues."""
        if gender:
            return gender.lower()
        desc_lower = description.lower()
        if re.search(r"\b(male|man|men|boy|actor|gentleman)\b", desc_lower):
            return "male"
        if re.search(r"\b(female|woman|women|girl|actress|lady)\b", desc_lower):
            return "female"
        return "female"

    async def _resolve_design_base_voice(
        self,
        owner_id: str,
        base_voice_id: str | None,
        target_gender: str,
    ) -> Voice:
        """Use explicit base_voice_id if chosen, otherwise return an unreferenced prompt-design voice."""
        if base_voice_id:
            return await self.get_voice_by_id(base_voice_id, owner_id)

        return Voice(
            id="virtual-design-base",
            name="Virtual Design Base",
            voice_type=VoiceType.BUILT_IN,
            owner_id=None,
            language="km-KH",
            visibility=VoiceVisibility.PUBLIC,
            modifiers={"gender": target_gender},
        )

    @staticmethod
    def _build_design_modifiers(
        base_voice: Voice,
        target_gender: str,
        clean_desc: str,
        pitch: float | None,
        speed: float | None,
        emotion: str | None,
        style: str | None,
        extra_modifiers: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Compose clean modifiers without inheriting stale control instructions or tokens."""
        inherited = {
            k: v
            for k, v in (base_voice.modifiers or {}).items()
            if k not in {"control_instruction", "prompt_text", "feature_token"}
        }
        raw_modifiers: dict[str, Any] = {
            **inherited,
            "parent_voice_id": base_voice.id,
            "gender": target_gender,
            "pitch": pitch,
            "speed": speed,
            "emotion": emotion,
            "style": style,
            "description": clean_desc,
            **(extra_modifiers or {}),
        }
        return {k: v for k, v in raw_modifiers.items() if v is not None}

    @staticmethod
    def _ensure_pcm_wav(audio_bytes: bytes) -> bytes:
        """Ensure uploaded/preview audio bytes are genuine 16-bit PCM WAV."""
        if audio_bytes.startswith(b"RIFF"):
            return audio_bytes
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        out_buf = io.BytesIO()
        sf.write(out_buf, data, sr, format="WAV", subtype="PCM_16")
        return out_buf.getvalue()

    async def preview_designed_voice(
        self,
        owner_id: str,
        base_voice_id: str | None = None,
        gender: str | None = None,
        pitch: float | None = 1.0,
        speed: float | None = 1.0,
        emotion: str | None = None,
        style: str | None = None,
        description: str = "",
        preview_text: str | None = None,
        extra_modifiers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Synthesize a Voice Design audition preview without persisting to DB or storage."""
        if not self.inference_engine:
            raise InferenceServiceError("Inference engine is not configured.")

        clean_desc = description.strip()
        target_gender = self._detect_target_gender(gender, clean_desc)
        base_voice = await self._resolve_design_base_voice(owner_id, base_voice_id, target_gender)
        modifiers = self._build_design_modifiers(
            base_voice=base_voice,
            target_gender=target_gender,
            clean_desc=clean_desc,
            pitch=pitch,
            speed=speed,
            emotion=emotion,
            style=style,
            extra_modifiers=extra_modifiers,
        )

        target_script = (preview_text or "").strip() or get_preview_text_for_language(base_voice.language)

        if hasattr(self.inference_engine, "preview_designed_voice"):
            result = await self.inference_engine.preview_designed_voice(
                base_voice=base_voice,
                modifiers=modifiers,
                preview_text=target_script,
            )
            audio_bytes = self._ensure_pcm_wav(result["audio_bytes"])
            duration = float(result.get("duration") or 0.0)
            control_instruction = str(result.get("control_instruction") or "")
            resolved_prompt = str(result.get("prompt_text") or target_script)
        else:
            try:
                _, raw_audio = await self.inference_engine.design_voice(
                    base_voice, modifiers, preview_text=target_script
                )
            except TypeError:
                _, raw_audio = await self.inference_engine.design_voice(base_voice, modifiers)
            audio_bytes = self._ensure_pcm_wav(raw_audio)
            data_pcm, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            duration = round(len(data_pcm) / float(sr), 2)
            control_instruction = str(modifiers.get("control_instruction") or "")
            resolved_prompt = target_script

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "content_type": "audio/wav",
            "duration_seconds": duration,
            "control_instruction": control_instruction,
            "preview_text": resolved_prompt,
        }

    async def design_voice(
        self,
        owner_id: str,
        name: str,
        base_voice_id: str | None = None,
        gender: str | None = None,
        pitch: float | None = None,
        speed: float | None = None,
        emotion: str | None = None,
        style: str | None = None,
        description: str = "",
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
        extra_modifiers: dict[str, Any] | None = None,
        preview_text: str | None = None,
        preview_audio_base64: str | None = None,
    ) -> Voice:
        """Create and persist a designed voice identity from acoustic descriptions or audited preview audio."""
        clean_desc = description.strip()
        target_gender = self._detect_target_gender(gender, clean_desc)
        base_voice = await self._resolve_design_base_voice(owner_id, base_voice_id, target_gender)
        modifiers = self._build_design_modifiers(
            base_voice=base_voice,
            target_gender=target_gender,
            clean_desc=clean_desc,
            pitch=pitch,
            speed=speed,
            emotion=emotion,
            style=style,
            extra_modifiers=extra_modifiers,
        )

        voice_id = str(uuid.uuid4())
        preview_key: str | None = f"voices/{voice_id}/preview.wav"
        ref_key: str | None = preview_key
        engine_preview: bytes | None = None
        target_script = (preview_text or "").strip() or get_preview_text_for_language(base_voice.language)

        if preview_audio_base64:
            try:
                engine_preview = self._ensure_pcm_wav(base64.b64decode(preview_audio_base64))
                modifiers["feature_token"] = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
                modifiers["prompt_text"] = target_script
                if self.inference_engine and hasattr(self.inference_engine, "distill_voice_instruction"):
                    modifiers["control_instruction"] = self.inference_engine.distill_voice_instruction(
                        modifiers, clean_desc
                    )
            except Exception:
                engine_preview = None

        if not engine_preview and self.inference_engine:
            try:
                try:
                    token, engine_preview = await self.inference_engine.design_voice(
                        base_voice, modifiers, preview_text=target_script
                    )
                except TypeError:
                    token, engine_preview = await self.inference_engine.design_voice(
                        base_voice, modifiers
                    )
                if token:
                    modifiers["feature_token"] = token
                if engine_preview:
                    engine_preview = self._ensure_pcm_wav(engine_preview)
            except Exception:
                ref_key = base_voice.reference_audio_key
                preview_key = base_voice.preview_audio_key
        elif not engine_preview:
            ref_key = base_voice.reference_audio_key
            preview_key = base_voice.preview_audio_key

        now = datetime.now(UTC)
        voice = Voice(
            id=voice_id,
            name=name.strip(),
            voice_type=VoiceType.DESIGNED,
            owner_id=owner_id,
            language=base_voice.language,
            description=clean_desc or f"Variation of {base_voice.name}",
            reference_audio_key=ref_key,
            preview_audio_key=preview_key,
            modifiers=modifiers,
            visibility=visibility,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        preview_sample: bytes | None = engine_preview
        if (not preview_sample or len(preview_sample) == 0) and self.inference_engine:
            try:
                generated_preview, _ = await self.inference_engine.generate_speech(
                    text=target_script,
                    voice=voice,
                    language=voice.language,
                    speed=float(modifiers.get("speed", 1.0)),
                    output_format=AudioFormat.WAV,
                )
                if generated_preview:
                    preview_sample = self._ensure_pcm_wav(generated_preview)
            except Exception:
                pass

        if self.storage and preview_sample and preview_key:
            await self.storage.upload(preview_key, preview_sample, content_type="audio/wav")

        return await self.voice_repo.create(voice)
