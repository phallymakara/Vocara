"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Vocara API application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Environment
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Vocara Voice API Platform"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Security
    API_KEY_SALT: str = Field(default="dev-salt-change-in-production")
    SECRET_KEY: str = Field(default="dev-secret-change-in-production")
    CORS_ORIGINS: list[str] | str = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # PostgreSQL Database
    DATABASE_URL: str = "postgresql+asyncpg://vocara_user:vocara_password@localhost:5432/vocara_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20

    # Storage Backend
    STORAGE_BACKEND: Literal["local", "azure", "r2"] = "local"
    LOCAL_STORAGE_DIR: str = "./storage_local"

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str | None = None
    AZURE_STORAGE_CONTAINER_NAME: str = "vocara-audio"

    # Cloudflare R2 / S3
    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str = "vocara-audio"
    R2_PUBLIC_URL_PREFIX: str | None = None

    # Inference Engine (fake | modal | huggingface)
    INFERENCE_ENGINE_TYPE: Literal["fake", "modal", "huggingface"] = "fake"
    MODAL_API_ENDPOINT: str | None = None
    MODAL_API_TOKEN: str | None = None
    HUGGINGFACE_API_KEY: str | None = None
    HUGGINGFACE_ENDPOINT_URL: str | None = None
    HUGGINGFACE_MODEL_ID: str = "openbmb/VoxCPM2"
    INFERENCE_TIMEOUT_SECONDS: int = 60

    # Rate Limiting & Quotas
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_CHAR_QUOTA_PER_MONTH: int = 100000
    ASYNC_CHAR_THRESHOLD: int = 2000

    # Background Worker
    WORKER_QUEUE_NAME: str = "jobs:inference"
    WORKER_POLL_TIMEOUT_SECONDS: int = 2

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Support JSON arrays, comma-separated strings, or string lists for CORS origins."""
        import json

        if isinstance(value, str):
            val = value.strip()
            if not val:
                return []
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in val.split(",") if origin.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Halt startup if insecure settings are configured in production environment."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError(
                    "Insecure Configuration: DEBUG must be set to False in production environment."
                )
            if "dev-salt" in self.API_KEY_SALT or len(self.API_KEY_SALT) < 32:
                raise ValueError(
                    "Insecure Configuration: API_KEY_SALT must be a high-entropy secret "
                    "(at least 32 characters) in production."
                )
            if "dev-secret" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Insecure Configuration: SECRET_KEY must be a high-entropy secret "
                    "(at least 32 characters) in production."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for cached configuration settings."""
    return Settings()
