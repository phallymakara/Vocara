"""API endpoints for user registration, email/password login, and Google OAuth."""

from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from vocara.api.deps import CurrentUser, UserAuthServiceDep
from vocara.api.v1.schemas.auth import (
    AuthSessionResponse,
    LoginRequest,
    RegisterRequest,
    UserProfileResponse,
)
from vocara.domain.entities import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _to_user_profile(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        plan=user.plan,
        has_google=bool(user.google_sub),
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthSessionResponse,
    summary="Register with Email & Password",
)
async def register(
    payload: RegisterRequest,
    user_auth_service: UserAuthServiceDep,
) -> AuthSessionResponse:
    """Create a new user account and auto-provision a Free Plan API key."""
    user, token, raw_api_key = await user_auth_service.register_with_email(
        name=payload.name,
        email=payload.email,
        password=payload.password,
    )
    return AuthSessionResponse(
        access_token=token,
        user=_to_user_profile(user),
        default_api_key=raw_api_key,
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="Login with Email & Password",
)
async def login(
    payload: LoginRequest,
    user_auth_service: UserAuthServiceDep,
) -> AuthSessionResponse:
    """Authenticate an existing user with email and password."""
    user, token = await user_auth_service.login_with_email(
        email=payload.email,
        password=payload.password,
    )
    return AuthSessionResponse(
        access_token=token,
        user=_to_user_profile(user),
    )


@router.get(
    "/google/login",
    summary="Start Google OAuth 2.0 Login",
)
async def google_login(user_auth_service: UserAuthServiceDep) -> RedirectResponse:
    """Redirect browser to Google OAuth consent screen."""
    url = user_auth_service.get_google_login_url()
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    summary="Google OAuth 2.0 Callback",
)
async def google_callback(
    request: Request,
    user_auth_service: UserAuthServiceDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Handle Google OAuth callback, provision Free Plan key if new, and redirect to frontend."""
    frontend_base = request.app.state.settings.FRONTEND_APP_URL.rstrip("/")
    if error or not code or not state:
        err_msg = error or "Google sign-in was cancelled."
        return RedirectResponse(
            url=f"{frontend_base}/login?{urlencode({'error': err_msg})}",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        _, token, raw_api_key = await user_auth_service.authenticate_google_callback(
            code=code, state=state
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"{frontend_base}/login?{urlencode({'error': str(exc)})}",
            status_code=status.HTTP_302_FOUND,
        )

    fragment_params: dict[str, str] = {"token": token}
    if raw_api_key:
        fragment_params["api_key"] = raw_api_key
    return RedirectResponse(
        url=f"{frontend_base}/auth/callback#{urlencode(fragment_params)}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User Profile",
)
async def get_me(current_user: CurrentUser) -> UserProfileResponse:
    """Return the authenticated user's profile and active plan."""
    return _to_user_profile(current_user)

