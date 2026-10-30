"""Base class and common utilities for inference engine adapters."""

import asyncio
from abc import ABC
from typing import Any

import structlog

from vocara.core.exceptions import InferenceServiceError
from vocara.domain.ports import InferenceEngine

logger = structlog.get_logger("vocara.inference")


class BaseInferenceEngine(InferenceEngine, ABC):
    """Abstract base class for inference engines with built-in retry and timeout handling."""

    def __init__(self, timeout_seconds: int = 60, max_retries: int = 2) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def _execute_with_retry(
        self, operation_name: str, coro_fn: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute inference operation with timeout and transient retry logic."""
        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    coro_fn(*args, **kwargs),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError as err:
                logger.warning(
                    "inference_timeout",
                    operation=operation_name,
                    attempt=attempt,
                    timeout=self.timeout_seconds,
                )
                last_exception = err
            except Exception as err:
                logger.warning(
                    "inference_transient_error",
                    operation=operation_name,
                    attempt=attempt,
                    error=str(err),
                )
                last_exception = err

            if attempt < self.max_retries:
                await asyncio.sleep(0.5 * attempt)

        raise InferenceServiceError(
            f"Operation '{operation_name}' failed after {self.max_retries} attempts: "
            f"{last_exception}"
        )
