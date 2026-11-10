"""API endpoints for system discovery, formats, and language catalogs."""

from fastapi import APIRouter, Request

from vocara.api.deps import VoiceServiceDep
from vocara.api.v1.schemas.system import FormatInfo, LanguageInfo
from vocara.domain.constants import get_preview_text_for_language

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/languages",
    response_model=list[LanguageInfo],
    summary="List Supported Languages",
)
async def list_languages(
    request: Request,
    voice_service: VoiceServiceDep,
) -> list[LanguageInfo]:
    """Retrieve catalog of supported speech synthesis languages and active voice count."""
    settings = getattr(request.app.state, "settings", None)
    km_preview = get_preview_text_for_language(
        "km-KH",
        km_default=getattr(settings, "DEFAULT_PREVIEW_TEXT_KM", None),
        en_default=getattr(settings, "DEFAULT_PREVIEW_TEXT_EN", None),
    )
    en_preview = get_preview_text_for_language(
        "en-US",
        km_default=getattr(settings, "DEFAULT_PREVIEW_TEXT_KM", None),
        en_default=getattr(settings, "DEFAULT_PREVIEW_TEXT_EN", None),
    )

    all_voices = await voice_service.list_voices(owner_id="", limit=100)

    km_count = sum(1 for v in all_voices if v.language.lower() == "km-kh")
    en_count = sum(1 for v in all_voices if v.language.lower() == "en-us")

    return [
        LanguageInfo(
            code="km-KH",
            name="Khmer",
            native_name="ភាសាខ្មែរ",
            voice_count=km_count,
            is_default=True,
            default_preview_text=km_preview,
        ),
        LanguageInfo(
            code="en-US",
            name="English (United States)",
            native_name="English",
            voice_count=en_count,
            is_default=False,
            default_preview_text=en_preview,
        ),
        LanguageInfo(
            code="mixed",
            name="Mixed (Khmer & English)",
            native_name="ភាសាខ្មែរ / English (Code-Switching)",
            voice_count=km_count + en_count,
            is_default=False,
            default_preview_text=km_preview,
        ),
    ]


@router.get(
    "/formats",
    response_model=list[FormatInfo],
    summary="List Supported Audio Formats",
)
async def list_formats(request: Request) -> list[FormatInfo]:
    """Retrieve audio encoding profiles and playback specifications."""
    settings = getattr(request.app.state, "settings", None)
    sample_rate_hz = int(getattr(settings, "AUDIO_SAMPLE_RATE_HZ", 48000))
    return [
        FormatInfo(
            format="mp3",
            content_type="audio/mpeg",
            sample_rate_hz=sample_rate_hz,
            channels="mono",
            bit_depth=16,
            description=(
                "Compressed MPEG audio format. Recommended for web streaming and low latency."
            ),
        ),
        FormatInfo(
            format="wav",
            content_type="audio/wav",
            sample_rate_hz=sample_rate_hz,
            channels="mono",
            bit_depth=16,
            description=(
                "Uncompressed linear PCM audio. Recommended for high-fidelity audio pipelines."
            ),
        ),
        FormatInfo(
            format="flac",
            content_type="audio/flac",
            sample_rate_hz=sample_rate_hz,
            channels="mono",
            bit_depth=16,
            description=(
                "Lossless compressed audio. Recommended for archiving and studio production."
            ),
        ),
        FormatInfo(
            format="ogg",
            content_type="audio/ogg",
            sample_rate_hz=sample_rate_hz,
            channels="mono",
            bit_depth=16,
            description=(
                "Ogg Vorbis container format. Recommended for open-standard web applications."
            ),
        ),
    ]
