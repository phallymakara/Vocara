"""API v1 master router aggregating all domain sub-routers."""

from fastapi import APIRouter

from vocara.api.v1.endpoints.auth import router as auth_router
from vocara.api.v1.endpoints.jobs import router as jobs_router
from vocara.api.v1.endpoints.keys import router as keys_router
from vocara.api.v1.endpoints.system import router as system_router
from vocara.api.v1.endpoints.tts import router as tts_router
from vocara.api.v1.endpoints.usage import router as usage_router
from vocara.api.v1.endpoints.voices import router as voices_router
from vocara.api.v1.endpoints.webhooks import router as webhooks_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(keys_router)
api_v1_router.include_router(usage_router)
api_v1_router.include_router(voices_router)
api_v1_router.include_router(tts_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(system_router)
