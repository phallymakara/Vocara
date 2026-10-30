"""API endpoints for Asynchronous Job Tracking and Result Retrieval."""

from fastapi import APIRouter, Query, Response

from vocara.api.deps import CurrentApiKey, JobServiceDep
from vocara.api.v1.schemas.job import JobResponse
from vocara.domain.entities import Job

router = APIRouter(prefix="/jobs", tags=["Job Tracking"])


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


@router.get(
    "",
    response_model=list[JobResponse],
    summary="List Jobs",
)
async def list_jobs(
    current_key: CurrentApiKey,
    job_service: JobServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[JobResponse]:
    """List historical synthesis and cloning jobs initiated by developer account."""
    jobs = await job_service.list_jobs(owner_id=current_key.owner_id, skip=skip, limit=limit)
    return [_to_job_response(j) for j in jobs]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get Job Status",
)
async def get_job_status(
    job_id: str,
    current_key: CurrentApiKey,
    job_service: JobServiceDep,
) -> JobResponse:
    """Check the status (queued, processing, completed, failed) of an asynchronous job."""
    job = await job_service.get_job(job_id=job_id, owner_id=current_key.owner_id)
    return _to_job_response(job)


@router.get(
    "/{job_id}/result",
    summary="Download Job Audio Result",
)
async def get_job_result(
    job_id: str,
    current_key: CurrentApiKey,
    job_service: JobServiceDep,
) -> Response:
    """Stream or download the completed audio artifact for an asynchronous job."""
    audio_bytes, media_type = await job_service.get_job_audio(
        job_id=job_id, owner_id=current_key.owner_id
    )

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="job_{job_id}_result.mp3"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
