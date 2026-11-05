"""API endpoints for Voice Library management and preview streaming."""

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile, status

from vocara.api.deps import CurrentApiKey, OptionalApiKey, VoiceServiceDep
from vocara.api.v1.schemas.voice import (
    DesignVoiceRequest,
    UpdateVoiceRequest,
    VoiceResponse,
)
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility

router = APIRouter(prefix="/voices", tags=["Voice Library"])


def _to_voice_response(voice: Voice, preview_url: str | None = None) -> VoiceResponse:
    """Format domain entity into HTTP DTO."""
    return VoiceResponse(
        id=voice.id,
        name=voice.name,
        voice_type=voice.voice_type,
        owner_id=voice.owner_id,
        language=voice.language,
        description=voice.description,
        visibility=voice.visibility,
        modifiers=voice.modifiers,
        preview_url=preview_url or f"/api/v1/voices/{voice.id}/preview",
        created_at=voice.created_at,
        updated_at=voice.updated_at,
    )


@router.get(
    "",
    response_model=list[VoiceResponse],
    summary="List Accessible Voices",
)
async def list_voices(
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
    language: str | None = Query(default=None, description="Filter by language code (e.g. km-KH)"),
    voice_type: VoiceType | None = Query(
        default=None, description="Filter by type (built_in, cloned, designed)"
    ),
    skip: int = Query(default=0, ge=0, description="Items to skip"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum items to return"),
) -> list[VoiceResponse]:
    """List built-in public voices and developer's own private voices."""
    voices = await voice_service.list_voices(
        owner_id=current_key.owner_id,
        language=language,
        voice_type=voice_type,
        skip=skip,
        limit=limit,
    )
    return [_to_voice_response(v) for v in voices]


@router.get(
    "/{voice_id}",
    response_model=VoiceResponse,
    summary="Get Voice Details",
)
async def get_voice(
    voice_id: str,
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
) -> VoiceResponse:
    """Retrieve full details of a specific voice."""
    voice = await voice_service.get_voice_by_id(voice_id=voice_id, owner_id=current_key.owner_id)
    return _to_voice_response(voice)


@router.patch(
    "/{voice_id}",
    response_model=VoiceResponse,
    summary="Update Voice Metadata",
)
async def update_voice(
    voice_id: str,
    payload: UpdateVoiceRequest,
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
) -> VoiceResponse:
    """Update name, description, visibility, or modifiers of a custom voice."""
    updated = await voice_service.update_voice(
        voice_id=voice_id,
        owner_id=current_key.owner_id,
        name=payload.name,
        description=payload.description,
        visibility=payload.visibility,
        modifiers=payload.modifiers,
    )
    return _to_voice_response(updated)


@router.delete(
    "/{voice_id}",
    summary="Delete Voice",
)
async def delete_voice(
    voice_id: str,
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
) -> dict[str, str]:
    """Soft-delete a custom voice (built-in voices cannot be deleted)."""
    await voice_service.delete_voice(voice_id=voice_id, owner_id=current_key.owner_id)
    return {"status": "deleted", "voice_id": voice_id}


@router.get(
    "/{voice_id}/preview",
    summary="Stream Voice Preview Audio",
)
async def get_voice_preview(
    voice_id: str,
    request: Request,
    voice_service: VoiceServiceDep,
    current_key: OptionalApiKey = None,
) -> Response:
    """Stream audio sample preview for the specified voice."""
    owner_id = current_key.owner_id if current_key else ""
    if not owner_id and getattr(request.app.state.settings, "ENVIRONMENT", "") == "development":
        owner_id = "default_developer"

    audio_bytes, content_type = await voice_service.get_preview_stream(
        voice_id=voice_id, owner_id=owner_id
    )

    ext = "mp3" if "mpeg" in content_type else "wav"
    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{voice_id}_preview.{ext}"',
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        },
    )


@router.post(
    "/clone",
    response_model=VoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone Voice Profile",
)
async def clone_voice(
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
    file: UploadFile = File(..., description="Reference audio file (WAV, MP3, OGG, FLAC, M4A, WebM)"),
    name: str = Form(..., min_length=2, max_length=100, description="Voice profile name"),
    consent_confirmed: bool = Form(
        ..., description="Explicit consent confirmation from the voice owner"
    ),
    language: str = Form(default="km-KH", description="Primary spoken language (e.g. km-KH)"),
    description: str = Form(default="", max_length=2000, description="Optional description"),
    visibility: VoiceVisibility = Form(
        default=VoiceVisibility.PRIVATE, description="Voice visibility"
    ),
    enhance_audio: bool = Form(
        default=True, description="Enable automated subtle noise reduction and gentle rumble removal"
    ),
    prompt_text: str = Form(
        default="",
        description="Optional transcript of what was spoken in the reference audio to enable Ultimate Voice Cloning (95%+ match)",
    ),
) -> VoiceResponse:
    """Upload reference audio to create a cloned voice profile.

    Requires explicit consent confirmation (consent_confirmed=true).
    """
    audio_bytes = await file.read()
    cloned = await voice_service.clone_voice(
        owner_id=current_key.owner_id,
        name=name,
        audio_bytes=audio_bytes,
        consent_confirmed=consent_confirmed,
        language=language,
        description=description,
        visibility=visibility,
        enhance_audio=enhance_audio,
        prompt_text=prompt_text,
    )
    return _to_voice_response(cloned)


@router.post(
    "/design",
    response_model=VoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Design Voice Variation",
)
async def design_voice(
    payload: DesignVoiceRequest,
    current_key: CurrentApiKey,
    voice_service: VoiceServiceDep,
) -> VoiceResponse:
    """Create a derivative voice profile variation from an existing base voice."""
    designed = await voice_service.design_voice(
        owner_id=current_key.owner_id,
        name=payload.name,
        base_voice_id=payload.base_voice_id,
        gender=payload.gender,
        pitch=payload.pitch,
        speed=payload.speed,
        emotion=payload.emotion,
        style=payload.style,
        description=payload.description,
        visibility=payload.visibility,
        extra_modifiers=payload.extra_modifiers,
    )
    return _to_voice_response(designed)
