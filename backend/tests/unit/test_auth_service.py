"""Unit tests for AuthService and UsageService."""

import pytest

from vocara.core.config import Settings
from vocara.core.exceptions import (
    AuthorizationError,
    InvalidApiKeyError,
    QuotaExceededError,
)
from vocara.domain.entities import ApiKey, UsageRecord
from vocara.domain.enums import ApiKeyStatus
from vocara.domain.ports import ApiKeyRepository, UsageRepository
from vocara.services.auth_service import AuthService
from vocara.services.usage_service import UsageService


class InMemoryApiKeyRepo(ApiKeyRepository):
    """In-memory fake implementation of ApiKeyRepository for fast unit tests."""

    def __init__(self) -> None:
        self.keys: dict[str, ApiKey] = {}

    async def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        for k in self.keys.values():
            if k.key_prefix == key_prefix and k.status == ApiKeyStatus.ACTIVE:
                return k
        return None

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        return self.keys.get(key_id)

    async def list_by_owner(self, owner_id: str) -> list[ApiKey]:
        return [k for k in self.keys.values() if k.owner_id == owner_id]

    async def create(self, api_key: ApiKey) -> ApiKey:
        self.keys[api_key.id] = api_key
        return api_key

    async def update_name(self, key_id: str, name: str) -> ApiKey | None:
        if key_id in self.keys:
            self.keys[key_id].name = name
            return self.keys[key_id]
        return None

    async def revoke(self, key_id: str) -> bool:
        if key_id in self.keys:
            self.keys[key_id].status = ApiKeyStatus.REVOKED
            return True
        return False

    async def delete(self, key_id: str) -> bool:
        return self.keys.pop(key_id, None) is not None

    async def increment_usage(self, key_id: str, characters: int) -> None:
        if key_id in self.keys:
            self.keys[key_id].chars_used_this_month += characters


class InMemoryUsageRepo(UsageRepository):
    """In-memory fake implementation of UsageRepository."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def record_usage(self, record: UsageRecord) -> None:
        self.records.append(record)

    async def get_monthly_usage(self, owner_id: str, year: int, month: int) -> int:
        return sum(
            r.characters_processed
            for r in self.records
            if r.owner_id == owner_id and r.timestamp.year == year and r.timestamp.month == month
        )

    async def get_monthly_analytics(
        self, owner_id: str, year: int, month: int, tz_offset_minutes: int = 0
    ) -> dict:
        matching = [
            r
            for r in self.records
            if r.owner_id == owner_id and r.timestamp.year == year and r.timestamp.month == month
        ]
        return {
            "total_requests": len(matching),
            "total_audio_seconds": sum(r.duration_seconds for r in matching),
            "daily_usage": [],
            "by_operation": [],
            "monthly_usage": [],
            "hourly_usage": [],
            "hourly_by_date": {},
            "by_key": {},
        }


@pytest.fixture
def auth_service(test_settings: Settings) -> AuthService:
    return AuthService(InMemoryApiKeyRepo(), test_settings)


@pytest.fixture
def usage_service() -> UsageService:
    return UsageService(InMemoryUsageRepo(), InMemoryApiKeyRepo())


@pytest.mark.asyncio
async def test_auth_service_key_lifecycle(auth_service: AuthService) -> None:
    # 1. Create Key
    raw_key, entity = await auth_service.create_api_key(
        owner_id="dev_user_1",
        name="Production Key",
        is_live=True,
        char_quota_per_month=50000,
    )

    assert raw_key.startswith("voc_live_")
    assert entity.key_prefix == raw_key[:16]
    assert entity.status == ApiKeyStatus.ACTIVE

    # 2. Authenticate with valid key
    authenticated_key = await auth_service.authenticate_key(raw_key)
    assert authenticated_key.id == entity.id
    assert authenticated_key.owner_id == "dev_user_1"

    # 3. Authenticate with invalid format / wrong secret
    with pytest.raises(InvalidApiKeyError):
        await auth_service.authenticate_key("invalid_key_token")

    with pytest.raises(InvalidApiKeyError):
        # Correct prefix but corrupted secret
        corrupted = raw_key[:16] + "tampered_characters_that_do_not_match"
        await auth_service.authenticate_key(corrupted)

    # 4. Unauthorized revocation attempt
    with pytest.raises(AuthorizationError):
        await auth_service.revoke_key(owner_id="wrong_user", key_id=entity.id)

    # 5. Legitimate revocation
    revoked = await auth_service.revoke_key(owner_id="dev_user_1", key_id=entity.id)
    assert revoked is True

    # 6. Authenticating a revoked key raises InvalidApiKeyError
    with pytest.raises(InvalidApiKeyError):
        await auth_service.authenticate_key(raw_key)


def test_usage_service_quota_enforcement(usage_service: UsageService) -> None:
    key = ApiKey(
        id="key-1",
        key_prefix="voc_live_11112222",
        hashed_secret="hash",
        owner_id="user_1",
        name="Key 1",
        char_quota_per_month=1000,
        chars_used_this_month=800,
    )

    # 100 characters fits within remaining 200
    usage_service.check_quota(key, chars_needed=100)

    # 250 characters exceeds quota (800 + 250 = 1050 > 1000)
    with pytest.raises(QuotaExceededError) as exc_info:
        usage_service.check_quota(key, chars_needed=250)

    assert exc_info.value.code == "QUOTA_EXCEEDED"
