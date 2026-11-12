"""API endpoints for API Key lifecycle management."""

from fastapi import APIRouter, Header, Query, Request, status

from vocara.api.deps import AuthServiceDep, CurrentApiKey, OptionalApiKey
from vocara.api.v1.schemas.keys import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
    UpdateApiKeyRequest,
)

router = APIRouter(prefix="/keys", tags=["Account & Keys"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
    summary="Create a new API Key",
)
async def create_api_key(
    payload: CreateApiKeyRequest,
    request: Request,
    auth_service: AuthServiceDep,
    current_key: OptionalApiKey = None,
    x_owner_id: str | None = Header(default=None, alias="X-Owner-ID"),
) -> ApiKeyCreatedResponse:
    """Generate a new developer API key.

    The raw `api_key` secret is returned only once in this response and cannot be retrieved again.
    """
    default_owner = getattr(request.app.state.settings, "DEFAULT_DEV_OWNER_ID", "default_developer")
    # Derive owner from current key if authenticated, or initial onboarding header
    owner_id = current_key.owner_id if current_key else (x_owner_id or default_owner)

    raw_key, key_entity = await auth_service.create_api_key(
        owner_id=owner_id,
        name=payload.name,
        is_live=payload.is_live,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        char_quota_per_month=payload.char_quota_per_month,
    )

    return ApiKeyCreatedResponse(
        id=key_entity.id,
        name=key_entity.name,
        key_prefix=key_entity.key_prefix,
        status=key_entity.status.value,
        rate_limit_per_minute=key_entity.rate_limit_per_minute,
        char_quota_per_month=key_entity.char_quota_per_month,
        chars_used_this_month=key_entity.chars_used_this_month,
        last_used_at=key_entity.last_used_at,
        created_at=key_entity.created_at,
        api_key=raw_key,
    )


@router.get(
    "",
    response_model=list[ApiKeyResponse],
    summary="List API Keys",
)
async def list_api_keys(
    current_key: CurrentApiKey,
    auth_service: AuthServiceDep,
) -> list[ApiKeyResponse]:
    """List all API keys belonging to the authenticated account."""
    keys = await auth_service.list_keys(current_key.owner_id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            status=k.status.value,
            rate_limit_per_minute=k.rate_limit_per_minute,
            char_quota_per_month=k.char_quota_per_month,
            chars_used_this_month=k.chars_used_this_month,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.patch(
    "/{key_id}",
    response_model=ApiKeyResponse,
    summary="Update API Key Name",
)
async def update_api_key(
    key_id: str,
    payload: UpdateApiKeyRequest,
    current_key: CurrentApiKey,
    auth_service: AuthServiceDep,
) -> ApiKeyResponse:
    """Update an API key's label."""
    updated = await auth_service.update_key_name(
        owner_id=current_key.owner_id,
        key_id=key_id,
        name=payload.name,
    )
    return ApiKeyResponse(
        id=updated.id,
        name=updated.name,
        key_prefix=updated.key_prefix,
        status=updated.status.value,
        rate_limit_per_minute=updated.rate_limit_per_minute,
        char_quota_per_month=updated.char_quota_per_month,
        chars_used_this_month=updated.chars_used_this_month,
        last_used_at=updated.last_used_at,
        created_at=updated.created_at,
    )


@router.post(
    "/{key_id}/revoke",
    summary="Revoke an API Key",
)
async def revoke_api_key_action(
    key_id: str,
    current_key: CurrentApiKey,
    auth_service: AuthServiceDep,
) -> dict[str, str]:
    """Revoke an active API key immediately."""
    await auth_service.revoke_key(owner_id=current_key.owner_id, key_id=key_id)
    return {"status": "revoked", "key_id": key_id}


@router.delete(
    "/{key_id}",
    summary="Revoke or Delete an API Key",
)
async def delete_or_revoke_api_key(
    key_id: str,
    current_key: CurrentApiKey,
    auth_service: AuthServiceDep,
    permanent: bool = Query(default=False, description="Permanently delete the key instead of revoking"),
) -> dict[str, str]:
    """Revoke an API key by default, or permanently remove it when permanent=true."""
    if permanent:
        await auth_service.delete_key(owner_id=current_key.owner_id, key_id=key_id)
        return {"status": "deleted", "key_id": key_id}
    await auth_service.revoke_key(owner_id=current_key.owner_id, key_id=key_id)
    return {"status": "revoked", "key_id": key_id}
