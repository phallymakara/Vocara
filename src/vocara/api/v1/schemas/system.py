"""DTO schemas for system capability and catalog discovery."""

from pydantic import BaseModel


class LanguageInfo(BaseModel):
    """Supported natural language information."""

    code: str
    name: str
    native_name: str
    voice_count: int
    is_default: bool


class FormatInfo(BaseModel):
    """Audio output format and encoding specifications."""

    format: str
    content_type: str
    sample_rate_hz: int
    channels: str
    bit_depth: int
    description: str


class SystemInfoResponse(BaseModel):
    """Comprehensive system metadata and supported configurations."""

    languages: list[LanguageInfo]
    formats: list[FormatInfo]
