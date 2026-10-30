"""Shared schema definitions for API request and response DTOs."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload definition."""

    code: str = Field(..., description="Error identifier code")
    message: str = Field(..., description="Safe user-facing error description")


class ErrorResponse(BaseModel):
    """Standardized API error response wrapper."""

    error: ErrorDetail


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    skip: int = Field(default=0, ge=0, description="Offset items to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum items to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard generic envelope for paginated collection results."""

    items: list[T]
    total: int
    skip: int
    limit: int
