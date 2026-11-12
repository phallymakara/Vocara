"""User account registration, password login, and Google OAuth 2.0 service."""

import uuid
from urllib.parse import urlencode

import httpx

from vocara.core.config import Settings
from vocara.core.exceptions import AuthenticationError, ValidationError
from vocara.core.security import (
    create_access_token,
    create_oauth_state,
    hash_password,
    verify_oauth_state,
    verify_password,
)
from vocara.domain.entities import ApiKey, User
from vocara.domain.enums import ApiKeyStatus
from vocara.domain.ports import UserRepository
from vocara.services.auth_service import AuthService

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class UserAuthService:
    """Handles user registration, password login, Google OAuth, and Free-Plan key setup."""

    def __init__(
        self,
        user_repo: UserRepository,
        auth_service: AuthService,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.auth_service = auth_service
        self.settings = settings
        self._http_client = http_client

    def _issue_session_token(self, user: User) -> str:
        return create_access_token(
            subject=user.id,
            email=user.email,
            secret=self.settings.SECRET_KEY,
            expires_minutes=self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    async def _provision_free_plan_key(self, user: User) -> tuple[str, ApiKey]:
        """Auto-create the default Free Plan API key for a newly registered user."""
        return await self.auth_service.create_api_key(
            owner_id=user.id,
            name="Free Plan Key",
            is_live=True,
            rate_limit_per_minute=self.settings.FREE_PLAN_RATE_LIMIT_PER_MINUTE,
            char_quota_per_month=self.settings.FREE_PLAN_CHAR_QUOTA_PER_MONTH,
        )

    async def ensure_active_api_key(self, user: User) -> ApiKey:
        """Return an active API key for the user, provisioning a Free Plan key if needed."""
        keys = await self.auth_service.list_keys(user.id)
        for k in keys:
            if k.status == ApiKeyStatus.ACTIVE:
                return k
        _, created = await self._provision_free_plan_key(user)
        return created

    async def register_with_email(
        self, name: str, email: str, password: str
    ) -> tuple[User, str, str]:
        """Register a new user with email/password and auto-create a Free Plan API key."""
        clean_name = name.strip()
        clean_email = email.strip().lower()
        if len(clean_name) < 2:
            raise ValidationError("Name must be at least 2 characters.", field="name")
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise ValidationError("Please enter a valid email address.", field="email")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.", field="password")

        existing = await self.user_repo.get_by_email(clean_email)
        if existing:
            raise ValidationError("An account with this email already exists.", field="email")

        user = User(
            id=str(uuid.uuid4()),
            email=clean_email,
            name=clean_name,
            password_hash=hash_password(password),
            plan="free",
            is_active=True,
        )
        created_user = await self.user_repo.create(user)
        raw_api_key, _ = await self._provision_free_plan_key(created_user)
        token = self._issue_session_token(created_user)
        return created_user, token, raw_api_key

    async def login_with_email(self, email: str, password: str) -> tuple[User, str]:
        """Authenticate an existing user with email and password."""
        clean_email = email.strip().lower()
        user = await self.user_repo.get_by_email(clean_email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid email or password.")
        if not user.password_hash:
            raise AuthenticationError(
                "This account uses Google Sign-In. Please continue with Google."
            )
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        await self.ensure_active_api_key(user)
        return user, self._issue_session_token(user)

    def get_google_login_url(self) -> str:
        """Build the Google OAuth 2.0 authorization URL with CSRF state."""
        if not self.settings.GOOGLE_CLIENT_ID or not self.settings.GOOGLE_CLIENT_SECRET:
            raise ValidationError(
                "Google login is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        state = create_oauth_state(self.settings.SECRET_KEY)
        params = {
            "client_id": self.settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self.settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def authenticate_google_callback(
        self, code: str, state: str
    ) -> tuple[User, str, str | None]:
        """Exchange Google OAuth code, find/create user, and ensure Free Plan key."""
        if not verify_oauth_state(state, self.settings.SECRET_KEY):
            raise AuthenticationError("Invalid or expired Google login session.")
        if not self.settings.GOOGLE_CLIENT_ID or not self.settings.GOOGLE_CLIENT_SECRET:
            raise AuthenticationError("Google login is not configured.")

        close_client = False
        client = self._http_client
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            close_client = True

        try:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.GOOGLE_CLIENT_ID,
                    "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": self.settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise AuthenticationError("Failed to verify Google authorization code.")
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise AuthenticationError("Google access token was not returned.")

            info_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if info_resp.status_code != 200:
                raise AuthenticationError("Failed to retrieve Google profile information.")
            profile = info_resp.json()
        finally:
            if close_client:
                await client.aclose()

        google_sub = str(profile.get("sub") or "").strip()
        email = str(profile.get("email") or "").strip().lower()
        email_verified = bool(profile.get("email_verified", False))
        name = str(profile.get("name") or email.split("@")[0] or "Vocara User").strip()
        avatar_url = profile.get("picture")

        if not google_sub or not email or not email_verified:
            raise AuthenticationError("A verified Google email address is required.")

        user = await self.user_repo.get_by_google_sub(google_sub)
        initial_raw_key: str | None = None

        if not user:
            existing_by_email = await self.user_repo.get_by_email(email)
            if existing_by_email:
                existing_by_email.google_sub = google_sub
                if not existing_by_email.avatar_url and avatar_url:
                    existing_by_email.avatar_url = avatar_url
                user = await self.user_repo.update(existing_by_email)
            else:
                new_user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    name=name[:120],
                    avatar_url=avatar_url,
                    google_sub=google_sub,
                    plan="free",
                    is_active=True,
                )
                user = await self.user_repo.create(new_user)
                initial_raw_key, _ = await self._provision_free_plan_key(user)

        if not user.is_active:
            raise AuthenticationError("Your account has been disabled.")

        if initial_raw_key is None:
            await self.ensure_active_api_key(user)

        return user, self._issue_session_token(user), initial_raw_key

