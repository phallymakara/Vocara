"""DTO schemas for Voice Library entities and operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vocara.domain.enums import VoiceType, VoiceVisibility


class VoiceResponse(BaseModel):
    """Public voice profile metadata representation."""

    id: str
    name: str
    voice_type: VoiceType
    owner_id: str | None
    language: str
    description: str
    visibility: VoiceVisibility
    modifiers: dict[str, Any] = Field(default_factory=dict)
    preview_url: str | None = None
    created_at: datetime
    updated_at: datetime


class UpdateVoiceRequest(BaseModel):
    """Payload for updating custom voice metadata."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    visibility: VoiceVisibility | None = None
    modifiers: dict[str, Any] | None = None


class DesignPreviewRequest(BaseModel):
    """Payload for auditioning a voice design variation before saving."""

    base_voice_id: str | None = Field(
        default=None, description="ID of the parent voice to derive from"
    )
    gender: str | None = Field(
        default="female", description="Speaker gender profile: female, male, neutral"
    )
    pitch: float | None = Field(
        default=1.0, ge=0.5, le=2.0, description="Pitch modifier factor (0.5 - 2.0)"
    )
    speed: float | None = Field(
        default=1.0, ge=0.5, le=2.0, description="Speed modifier factor (0.5 - 2.0)"
    )
    emotion: str | None = Field(default=None, max_length=50, description="Target emotion tag")
    style: str | None = Field(default=None, max_length=50, description="Target speech style")
    description: str = Field(default="", max_length=2000)
    preview_text: str | None = Field(
        default=None, max_length=500, description="Custom conversational preview phrase"
    )
    extra_modifiers: dict[str, Any] = Field(default_factory=dict)


class DesignPreviewResponse(BaseModel):
    """Audition response containing synthesized preview audio before saving."""

    audio_base64: str
    content_type: str = "audio/wav"
    duration_seconds: float
    control_instruction: str
    preview_text: str


class DesignVoiceRequest(BaseModel):
    """Payload for creating a derivative voice design variation."""

    name: str = Field(..., min_length=2, max_length=100)
    base_voice_id: str | None = Field(
        default=None, description="ID of the parent voice to derive from"
    )
    gender: str | None = Field(
        default="female", description="Speaker gender profile: female, male, neutral"
    )
    pitch: float | None = Field(
        default=None, ge=0.5, le=2.0, description="Pitch modifier factor (0.5 - 2.0)"
    )
    speed: float | None = Field(
        default=None, ge=0.5, le=2.0, description="Speed modifier factor (0.5 - 2.0)"
    )
    emotion: str | None = Field(default=None, max_length=50, description="Target emotion tag")
    style: str | None = Field(default=None, max_length=50, description="Target speech style")
    description: str = Field(default="", max_length=2000)
    visibility: VoiceVisibility = Field(default=VoiceVisibility.PRIVATE)
    extra_modifiers: dict[str, Any] = Field(default_factory=dict)
    preview_text: str | None = Field(
        default=None, max_length=500, description="Preview text spoken in audited audio"
    )
    preview_audio_base64: str | None = Field(
        default=None, description="Pre-auditioned base64 WAV audio to persist directly"
    )
