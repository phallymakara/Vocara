"""DTO schemas for Text-to-Speech synthesis."""

from pydantic import BaseModel, Field

from vocara.domain.enums import AudioFormat


class TtsRequest(BaseModel):
    """Payload for text-to-speech generation requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Text content to convert into speech.",
    )
    voice_id: str = Field(..., description="ID of the voice profile to synthesize with.")
    language: str = Field(default="km-KH", description="Target language code (e.g. km-KH, en-US).")
    speed: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Speaking rate multiplier (0.5 to 2.0)."
    )
    output_format: AudioFormat = Field(
        default=AudioFormat.MP3, description="Desired audio encoding format (mp3, wav, flac, ogg)."
    )
    async_only: bool = Field(
        default=False,
        description="Force asynchronous background job generation even for short text.",
    )
