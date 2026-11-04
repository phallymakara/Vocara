"""API v1 endpoints package."""

from vocara.api.v1.endpoints.jobs import router as jobs_router
from vocara.api.v1.endpoints.keys import router as keys_router
from vocara.api.v1.endpoints.tts import router as tts_router
from vocara.api.v1.endpoints.usage import router as usage_router
from vocara.api.v1.endpoints.voices import router as voices_router

__all__ = [
    "keys_router",
    "usage_router",
    "voices_router",
    "tts_router",
    "jobs_router",
]
