"""DTO schemas for user authentication, registration, and session profiles."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Email + password account registration payload."""

    name: str = Field(..., min_length=2, max_length=120, description="Full or display name")
    email: str = Field(..., min_length=3, max_length=255, description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password")


class LoginRequest(BaseModel):
    """Email + password login payload."""

    email: str = Field(..., min_length=3, max_length=255, description="Email address")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class UserProfileResponse(BaseModel):
    """Public user profile returned in auth responses."""

    id: str
    email: str
    name: str
    avatar_url: str | None = None
    plan: str
    has_google: bool = False


class AuthSessionResponse(BaseModel):
    """Authenticated session response including JWT and optional newly provisioned Free Plan key."""

    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
    default_api_key: str | None = Field(
        default=None,
        description="Auto-created Free Plan API key returned upon first account registration.",
    )

