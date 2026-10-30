"""API v1 DTO Schemas package."""

from vocara.api.v1.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
)
from vocara.api.v1.schemas.job import JobResponse
from vocara.api.v1.schemas.keys import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
)
from vocara.api.v1.schemas.tts import TtsRequest
from vocara.api.v1.schemas.usage import UsageSummaryResponse
from vocara.api.v1.schemas.voice import UpdateVoiceRequest, VoiceResponse

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    "CreateApiKeyRequest",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "UsageSummaryResponse",
    "VoiceResponse",
    "UpdateVoiceRequest",
    "TtsRequest",
    "JobResponse",
]
