"""CLI entrypoint for Vocara background inference worker."""

import asyncio
import signal
import sys
from typing import Any

import structlog

from vocara.container import Container
from vocara.core.config import get_settings
from vocara.core.logging import setup_logging
from vocara.worker.handler import Worker

logger = structlog.get_logger("vocara.worker.main")


async def _run_worker() -> None:
    """Async main routine initializing dependencies and starting worker."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    logger.info("initializing_worker_container", env=settings.ENVIRONMENT)
    container = Container(settings)
    await container.initialize()

    worker = Worker(container)

    def handle_exit(sig: int, _: Any) -> None:
        logger.info("shutdown_signal_received", signal=sig)
        worker.stop()

    # Register OS signals
    try:
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
    except (ValueError, AttributeError):
        pass  # Windows or non-main thread fallback

    try:
        await worker.run_forever()
    finally:
        logger.info("shutting_down_worker_container")
        await container.shutdown()


def run() -> None:
    """Sync wrapper entrypoint for CLI command execution."""
    try:
        asyncio.run(_run_worker())
    except KeyboardInterrupt:
        logger.info("worker_interrupted_by_user")
        sys.exit(0)


if __name__ == "__main__":
    run()
