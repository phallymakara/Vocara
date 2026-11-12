"""API integration tests for email/password auth, Google OAuth, and Free Plan key setup."""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient

from vocara.core.security import create_oauth_state
from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility


@pytest.mark.asyncio
async def test_email_register_login_and_tts_with_free_plan_key(
    async_client: AsyncClient,
) -> None:
    # 1. Seed a public voice so newly registered user can synthesize immediately
    app = async_client._transport.app  # type: ignore[attr-defined]
    container = app.state.container
    async with container.session_factory() as session:
        v_repo = container.get_voice_repo(session)
        await v_repo.create(
            Voice(
                id="auth-test-voice-1",
                name="Public Test Voice",
                voice_type=VoiceType.BUILT_IN,
                owner_id=None,
                language="km-KH",
                visibility=VoiceVisibility.PUBLIC,
            )
        )
        await session.commit()

    # 2. Register with email & password
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Sokha",
            "email": "sokha@example.com",
            "password": "password123",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["access_token"]
    assert reg_data["default_api_key"].startswith("voc_live_")
    assert reg_data["user"]["email"] == "sokha@example.com"
    assert reg_data["user"]["plan"] == "free"

    jwt_headers = {"Authorization": f"Bearer {reg_data['access_token']}"}

    # 3. Duplicate registration is rejected
    dup_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Sokha 2",
            "email": "sokha@example.com",
            "password": "password123",
        },
    )
    assert dup_resp.status_code in (400, 422)

    # 4. /auth/me returns user profile
    me_resp = await async_client.get("/api/v1/auth/me", headers=jwt_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Sokha"

    # 5. Free Plan Key is automatically listed under /api/v1/keys
    keys_resp = await async_client.get("/api/v1/keys", headers=jwt_headers)
    assert keys_resp.status_code == 200
    keys = keys_resp.json()
    assert any(k["name"] == "Free Plan Key" and k["status"] == "active" for k in keys)

    # 6. User can synthesize speech immediately using their JWT session
    tts_resp = await async_client.post(
        "/api/v1/tts",
        json={
            "text": "សួស្តី",
            "voice_id": "auth-test-voice-1",
            "language": "km-KH",
            "output_format": "mp3",
        },
        headers=jwt_headers,
    )
    assert tts_resp.status_code == 200

    # 7. Login with wrong password fails, valid password succeeds
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "sokha@example.com", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    ok_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "sokha@example.com", "password": "password123"},
    )
    assert ok_login.status_code == 200
    assert ok_login.json()["access_token"]


@pytest.mark.asyncio
async def test_google_oauth_callback_creates_user_and_free_key(
    async_client: AsyncClient,
) -> None:
    app = async_client._transport.app  # type: ignore[attr-defined]
    settings = app.state.settings
    settings.GOOGLE_CLIENT_ID = "test-google-client-id"
    settings.GOOGLE_CLIENT_SECRET = "test-google-client-secret"

    def mock_google_handler(request: httpx.Request) -> httpx.Response:
        if "oauth2.googleapis.com/token" in str(request.url):
            return httpx.Response(200, json={"access_token": "mock-google-access-token"})
        if "openidconnect.googleapis.com/v1/userinfo" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "sub": "google-sub-12345",
                    "email": "dara.google@example.com",
                    "email_verified": True,
                    "name": "Dara Google",
                    "picture": "https://example.com/avatar.png",
                },
            )
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_google_handler))
    state = create_oauth_state(settings.SECRET_KEY)

    # Call service directly with mocked HTTP client to verify user + Free Plan key creation
    container = app.state.container
    async with container.session_factory() as session:
        user_auth = container.get_user_auth_service(session)
        user_auth._http_client = mock_client
        user, jwt_token, raw_key = await user_auth.authenticate_google_callback(
            code="mock-code", state=state
        )
        await session.commit()

    await mock_client.aclose()

    assert user.email == "dara.google@example.com"
    assert user.google_sub == "google-sub-12345"
    assert user.plan == "free"
    assert raw_key is not None and raw_key.startswith("voc_live_")

    # Verify JWT works for /api/v1/keys and shows the Free Plan Key
    keys_resp = await async_client.get(
        "/api/v1/keys",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert keys_resp.status_code == 200
    assert len(keys_resp.json()) == 1
    assert keys_resp.json()[0]["name"] == "Free Plan Key"

    # Verify /auth/google/login returns 302 redirect to Google with valid state
    login_redirect = await async_client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert login_redirect.status_code == 302
    parsed = urlparse(login_redirect.headers["location"])
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["test-google-client-id"]
    assert "state" in qs

