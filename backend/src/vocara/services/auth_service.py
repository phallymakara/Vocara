"""Authentication service for developer API keys."""

import uuid

from vocara.core.config import Settings
from vocara.core.exceptions import (
    AuthorizationError,
    EntityNotFoundError,
    InvalidApiKeyError,
)
from vocara.core.security import generate_api_key, hash_api_key, verify_api_key
from vocara.domain.entities import ApiKey
from vocara.domain.enums import ApiKeyStatus
from vocara.domain.ports import ApiKeyRepository


class AuthService:
    """Encapsulates developer authentication and API key lifecycle management."""

    def __init__(self, api_key_repo: ApiKeyRepository, settings: Settings) -> None:
        self.api_key_repo = api_key_repo
        self.settings = settings

    async def create_api_key(
        self,
        owner_id: str,
        name: str,
        is_live: bool = True,
        rate_limit_per_minute: int = 60,
        char_quota_per_month: int = 100000,
    ) -> tuple[str, ApiKey]:
        """Generate, hash, and persist a new developer API key.

        Returns:
            tuple[raw_api_key, api_key_entity]: Raw secret key is returned only once.
        """
        raw_key, prefix, _ = generate_api_key(is_live=is_live)
        hashed_secret = hash_api_key(raw_key, self.settings.API_KEY_SALT)

        entity = ApiKey(
            id=str(uuid.uuid4()),
            key_prefix=prefix,
            hashed_secret=hashed_secret,
            owner_id=owner_id,
            name=name,
            status=ApiKeyStatus.ACTIVE,
            rate_limit_per_minute=rate_limit_per_minute,
            char_quota_per_month=char_quota_per_month,
            chars_used_this_month=0,
        )

        persisted_entity = await self.api_key_repo.create(entity)
        return raw_key, persisted_entity

    async def authenticate_key(self, raw_key: str) -> ApiKey:
        """Authenticate an incoming raw API key in constant time."""
        if not raw_key or not (raw_key.startswith("voc_live_") or raw_key.startswith("voc_test_")):
            raise InvalidApiKeyError()

        # Prefix is 16 characters
        prefix = raw_key[:16]
        key_entity = await self.api_key_repo.get_by_prefix(prefix)
        if not key_entity or key_entity.status != ApiKeyStatus.ACTIVE:
            raise InvalidApiKeyError()

        is_valid = verify_api_key(raw_key, key_entity.hashed_secret, self.settings.API_KEY_SALT)
        if not is_valid:
            raise InvalidApiKeyError()

        return key_entity

    async def update_key_name(self, owner_id: str, key_id: str, name: str) -> ApiKey:
        """Rename an API key belonging to owner."""
        key_entity = await self.api_key_repo.get_by_id(key_id)
        if not key_entity:
            raise EntityNotFoundError("API key not found")

        if key_entity.owner_id != owner_id:
            raise AuthorizationError("You do not have permission to update this key.")

        updated = await self.api_key_repo.update_name(key_id, name.strip())
        if not updated:
            raise EntityNotFoundError("API key not found")
        return updated

    async def revoke_key(self, owner_id: str, key_id: str) -> bool:
        """Revoke an API key belonging to owner."""
        key_entity = await self.api_key_repo.get_by_id(key_id)
        if not key_entity:
            raise EntityNotFoundError("API key not found")

        if key_entity.owner_id != owner_id:
            raise AuthorizationError("You do not have permission to revoke this key.")

        return await self.api_key_repo.revoke(key_id)

    async def delete_key(self, owner_id: str, key_id: str) -> bool:
        """Permanently delete an API key belonging to owner."""
        key_entity = await self.api_key_repo.get_by_id(key_id)
        if not key_entity:
            raise EntityNotFoundError("API key not found")

        if key_entity.owner_id != owner_id:
            raise AuthorizationError("You do not have permission to delete this key.")

        return await self.api_key_repo.delete(key_id)

    async def list_keys(self, owner_id: str) -> list[ApiKey]:
        """List all API keys for developer account."""
        return await self.api_key_repo.list_by_owner(owner_id)

    async def get_or_create_dev_key(self) -> ApiKey:
        """Retrieve or create a default development API key for seamless local testing."""
        keys = await self.api_key_repo.list_by_owner("default_developer")
        for k in keys:
            if k.status == ApiKeyStatus.ACTIVE:
                return k

        _, dev_key = await self.create_api_key(
            owner_id="default_developer",
            name="Default Workspace Key",
            is_live=True,
            rate_limit_per_minute=120,
            char_quota_per_month=1_000_000,
        )
        return dev_key
