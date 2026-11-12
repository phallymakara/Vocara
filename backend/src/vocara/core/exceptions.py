"""Domain exception hierarchy for the Vocara Voice API Platform."""


class VocaraError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class EntityNotFoundError(VocaraError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(message, code)


class VoiceNotFoundError(EntityNotFoundError):
    """Raised when the specified voice ID does not exist or is inaccessible."""

    def __init__(self, voice_id: str) -> None:
        super().__init__(f"Voice with ID '{voice_id}' was not found.", code="VOICE_NOT_FOUND")


class JobNotFoundError(EntityNotFoundError):
    """Raised when the specified job ID does not exist."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job with ID '{job_id}' was not found.", code="JOB_NOT_FOUND")


class AuthenticationError(VocaraError):
    """Raised when API key is missing or invalid."""

    def __init__(self, message: str = "Authentication failed", code: str = "UNAUTHORIZED") -> None:
        super().__init__(message, code)


class InvalidApiKeyError(AuthenticationError):
    """Raised when API key is invalid or revoked."""

    def __init__(self) -> None:
        super().__init__("The provided API key is invalid or revoked.", code="INVALID_API_KEY")


class AuthorizationError(VocaraError):
    """Raised when the client lacks permission for the resource."""

    def __init__(self, message: str = "Permission denied", code: str = "FORBIDDEN") -> None:
        super().__init__(message, code)


class QuotaExceededError(VocaraError):
    """Raised when client exceeds their allocated monthly character quota."""

    def __init__(self, current_usage: int, quota: int) -> None:
        super().__init__(
            f"Monthly character quota exceeded ({current_usage}/{quota} chars used).",
            code="QUOTA_EXCEEDED",
        )


class RateLimitExceededError(VocaraError):
    """Raised when requests exceed rate limits."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Rate limit of {limit} requests per minute exceeded.",
            code="RATE_LIMIT_EXCEEDED",
        )


class ConsentRequiredError(VocaraError):
    """Raised when voice cloning is attempted without explicit consent confirmation."""

    def __init__(self) -> None:
        super().__init__(
            "Explicit consent confirmation is required to clone a voice.",
            code="CONSENT_REQUIRED",
        )


class InvalidAudioError(VocaraError):
    """Raised when provided audio sample fails validation."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid audio sample: {reason}", code="INVALID_AUDIO")


class InferenceServiceError(VocaraError):
    """Raised when backend AI voice synthesis fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Voice synthesis failed: {reason}", code="INFERENCE_FAILED")


class InvalidWebhookUrlError(VocaraError):
    """Raised when webhook URL does not satisfy protocol requirements."""

    def __init__(
        self, message: str = "Webhook URL must begin with 'http://' or 'https://'."
    ) -> None:
        super().__init__(message, code="INVALID_URL")


class ValidationError(VocaraError):
    """Raised when domain input validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
