"""Worker contracts and data payloads shared between API queue and inference workers."""

from typing import Any
from pydantic import BaseModel, Field


class InferenceJobPayload(BaseModel):
    """Payload dispatched to the inference worker queue."""

    job_id: str = Field(..., description="Unique job identifier")
    job_type: str = Field(..., description="tts_generation, voice_cloning, or voice_variation")
    text: str | None = Field(default=None, description="Input text to synthesize")
    voice_id: str | None = Field(default=None, description="ID of the voice to use")
    reference_audio_url: str | None = Field(
        default=None, description="URL or storage key of reference audio for cloning"
    )
    language: str = Field(default="km-KH", description="Target language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Playback speed")
    output_format: str = Field(default="mp3", description="Audio output format (mp3, wav, flac)")
    voice_modifiers: dict[str, Any] = Field(
        default_factory=dict, description="Modifiers like pitch, age, emotion"
    )


class InferenceJobResult(BaseModel):
    """Result returned by the inference worker after execution."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="completed or failed")
    output_audio_url: str | None = Field(
        default=None, description="Storage key or URL of synthesized audio"
    )
    audio_duration_seconds: float = Field(default=0.0, description="Duration in seconds")
    character_count: int = Field(default=0, description="Characters processed")
    error_message: str | None = Field(default=None, description="Error message if failed")
