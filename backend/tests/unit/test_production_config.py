"""Unit tests for production environment security validation and CORS configuration."""

import pytest
from pydantic import ValidationError

from vocara.core.config import Settings


VALID_SALT = "b735976ba4fc0425ff490fcc2c4d645e51db39c0e77f3b0807e3730afb1d7258"
VALID_SECRET = "070efddb647a88406d86f39fa73b5a26b5f585ae8526db40e17a97065b035378"


def test_development_mode_allows_defaults():
    """In development mode, default secrets and debug=True should be permitted."""
    settings = Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        API_KEY_SALT="dev-salt-change-in-production",
        SECRET_KEY="dev-secret-change-in-production",
    )
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True


def test_production_rejects_debug_true():
    """In production mode, DEBUG=True must be rejected."""
    with pytest.raises(ValidationError, match="DEBUG must be set to False in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            API_KEY_SALT=VALID_SALT,
            SECRET_KEY=VALID_SECRET,
        )


def test_production_rejects_dev_salt():
    """In production mode, development placeholder salt must be rejected."""
    with pytest.raises(ValidationError, match="API_KEY_SALT must be a high-entropy secret"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            API_KEY_SALT="dev-salt-change-in-production",
            SECRET_KEY=VALID_SECRET,
        )


def test_production_rejects_short_salt():
    """In production mode, short salt (< 32 chars) must be rejected."""
    with pytest.raises(ValidationError, match="API_KEY_SALT must be a high-entropy secret"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            API_KEY_SALT="short_salt_123",
            SECRET_KEY=VALID_SECRET,
        )


def test_production_rejects_dev_secret():
    """In production mode, development placeholder secret must be rejected."""
    with pytest.raises(ValidationError, match="SECRET_KEY must be a high-entropy secret"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            API_KEY_SALT=VALID_SALT,
            SECRET_KEY="dev-secret-change-in-production",
        )


def test_production_rejects_short_secret():
    """In production mode, short secret (< 32 chars) must be rejected."""
    with pytest.raises(ValidationError, match="SECRET_KEY must be a high-entropy secret"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            API_KEY_SALT=VALID_SALT,
            SECRET_KEY="short_jwt_secret",
        )


def test_production_valid_configuration():
    """In production mode, strong keys and DEBUG=False must pass cleanly."""
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        API_KEY_SALT=VALID_SALT,
        SECRET_KEY=VALID_SECRET,
        CORS_ORIGINS="http://localhost:3000,https://app.vocara.ai",
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.DEBUG is False
    assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://app.vocara.ai"]


def test_cors_origins_comma_separated_parsing():
    """CORS_ORIGINS should parse comma-separated string into list."""
    settings = Settings(
        ENVIRONMENT="development",
        CORS_ORIGINS="http://localhost:3000, http://127.0.0.1:3000, https://studio.vocara.ai",
    )
    assert settings.CORS_ORIGINS == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://studio.vocara.ai",
    ]


def test_cors_origins_list_passthrough():
    """CORS_ORIGINS should accept list directly."""
    settings = Settings(
        ENVIRONMENT="development",
        CORS_ORIGINS=["http://localhost:3000", "https://app.vocara.ai"],
    )
    assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://app.vocara.ai"]
