"""API endpoints for Text-to-Speech (TTS) synthesis."""

import time

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from vocara.api.deps import CurrentApiKey, TtsServiceDep
from vocara.api.v1.schemas.job import JobResponse
from vocara.api.v1.schemas.tts import TtsRequest
from vocara.domain.entities import Job

router = APIRouter(prefix="/tts", tags=["Speech"])


def _to_job_response(job: Job) -> JobResponse:
    """Format domain Job entity into DTO."""
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        owner_id=job.owner_id,
        voice_id=job.voice_id,
        char_count=job.char_count,
        language=job.language,
        output_format=job.output_format.value,
        audio_duration_seconds=job.audio_duration_seconds,
        error_message=job.error_message,
        result_url=f"/api/v1/jobs/{job.id}/result",
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "",
    summary="Generate Speech (TTS)",
    responses={
        200: {
            "description": "Real-time synthesized speech audio stream.",
            "content": {"audio/mpeg": {}, "audio/wav": {}},
        },
        202: {
            "description": "Asynchronous job accepted for long-form speech generation.",
            "model": JobResponse,
        },
    },
)
async def generate_speech(
    payload: TtsRequest,
    current_key: CurrentApiKey,
    tts_service: TtsServiceDep,
    request: Request,
) -> Response:
    """Turn text into natural speech.

    - Short text (< 250 chars) synthesizes immediately to audio stream (200 OK).
    - Long-form text (>= 250 chars or async_only=True) queues as job (202 Accepted).
    """
    t0 = time.perf_counter()
    audio_bytes, duration, format_str, job = await tts_service.synthesize_or_enqueue(
        api_key=current_key,
        text=payload.text,
        voice_id=payload.voice_id,
        language=payload.language,
        speed=payload.speed,
        output_format=payload.output_format,
        async_only=payload.async_only,
    )
    request.state.inference_time_ms = round((time.perf_counter() - t0) * 1000, 2)

    if audio_bytes is not None:
        media_type = "audio/mpeg" if format_str == "mp3" else f"audio/{format_str}"
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "X-Audio-Duration": str(duration),
                "Content-Disposition": f'inline; filename="synthesized_speech.{format_str}"',
            },
        )

    assert job is not None
    job_dto = _to_job_response(job)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=job_dto.model_dump(mode="json"),
        headers={"Location": f"/api/v1/jobs/{job.id}"},
    )
