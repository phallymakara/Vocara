"""Voice Library business logic service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from vocara.core.exceptions import (
    AuthorizationError,
    ConsentRequiredError,
    VoiceNotFoundError,
)
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.domain.ports import BlobStorage, InferenceEngine, VoiceRepository
from vocara.utils.audio import (
    generate_synthetic_tone_wav,
    normalize_audio_to_wav,
    validate_reference_audio,
)


class VoiceService:
    """Manages voice profile queries, cloning, variations, and audio previews."""

    def __init__(
        self,
        voice_repo: VoiceRepository,
        storage: BlobStorage | None = None,
        inference_engine: InferenceEngine | None = None,
    ) -> None:
        self.voice_repo = voice_repo
        self.storage = storage
        self.inference_engine = inference_engine

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
            voice.modifiers = modifiers

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
        voice = await self.get_voice_by_id(voice_id, owner_id)

        if self.storage and voice.preview_audio_key:
            try:
                audio_bytes = await self.storage.download(voice.preview_audio_key)
                content_type = (
                    "audio/mpeg" if voice.preview_audio_key.endswith(".mp3") else "audio/wav"
                )
                return audio_bytes, content_type
            except Exception:
                pass  # Fall through to synthetic fallback

        # Return synthesized PCM WAV tone preview
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
    ) -> Voice:
        """Clone a voice profile from reference audio after verifying explicit consent."""
        if not consent_confirmed:
            raise ConsentRequiredError()

        # Validate audio bounds and container header
        validate_reference_audio(audio_bytes)

        # Resample and normalize to standard 24kHz 16-bit mono WAV
        normalized_wav, duration = normalize_audio_to_wav(audio_bytes, target_sample_rate=24000)

        voice_id = str(uuid.uuid4())
        ref_key = f"voices/{voice_id}/reference.wav"
        preview_key = f"voices/{voice_id}/preview.wav"

        preview_sample = normalized_wav
        feature_token: str | None = None

        if self.inference_engine:
            try:
                feature_token, engine_preview = await self.inference_engine.clone_voice(
                    normalized_wav, language=language
                )
                if engine_preview:
                    preview_sample = engine_preview
            except Exception:
                pass  # Fall back to using normalized reference audio as preview

        if self.storage:
            await self.storage.upload(ref_key, normalized_wav, content_type="audio/wav")
            await self.storage.upload(preview_key, preview_sample, content_type="audio/wav")

        now = datetime.now(UTC)
        modifiers: dict[str, Any] = {
            "consent_verified": True,
            "consent_timestamp": now.isoformat(),
            "duration_seconds": round(duration, 2),
        }
        if feature_token:
            modifiers["feature_token"] = feature_token

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
        return await self.voice_repo.create(voice)

    async def design_voice(
        self,
        owner_id: str,
        name: str,
        base_voice_id: str,
        pitch: float | None = None,
        speed: float | None = None,
        emotion: str | None = None,
        style: str | None = None,
        description: str = "",
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
        extra_modifiers: dict[str, Any] | None = None,
    ) -> Voice:
        """Create a derivative voice profile variation from an existing base voice."""
        base_voice = await self.get_voice_by_id(base_voice_id, owner_id)

        raw_modifiers: dict[str, Any] = {
            **base_voice.modifiers,
            "parent_voice_id": base_voice.id,
            "pitch": pitch,
            "speed": speed,
            "emotion": emotion,
            "style": style,
            **(extra_modifiers or {}),
        }
        modifiers = {k: v for k, v in raw_modifiers.items() if v is not None}

        voice_id = str(uuid.uuid4())
        preview_key = f"voices/{voice_id}/preview.wav"
        ref_key = base_voice.reference_audio_key

        if self.inference_engine:
            try:
                token, engine_preview = await self.inference_engine.design_voice(
                    base_voice, modifiers
                )
                if token:
                    modifiers["feature_token"] = token
                if self.storage and engine_preview:
                    await self.storage.upload(preview_key, engine_preview, content_type="audio/wav")
            except Exception:
                preview_key = base_voice.preview_audio_key
        else:
            preview_key = base_voice.preview_audio_key

        now = datetime.now(UTC)
        voice = Voice(
            id=voice_id,
            name=name.strip(),
            voice_type=VoiceType.DESIGNED,
            owner_id=owner_id,
            language=base_voice.language,
            description=description.strip() or f"Variation of {base_voice.name}",
            reference_audio_key=ref_key,
            preview_audio_key=preview_key,
            modifiers=modifiers,
            visibility=visibility,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        return await self.voice_repo.create(voice)
