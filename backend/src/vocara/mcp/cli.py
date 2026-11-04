"""CLI entrypoint for running Vocara MCP Server over Stdio transport."""

import asyncio
import logging
import sys

from vocara.container import Container
from vocara.core.config import get_settings
from vocara.mcp.server import create_mcp_server


async def run_stdio() -> None:
    """Initialize container and run MCP Server over standard input/output."""
    settings = get_settings()

    # Route logs to stderr to protect stdout for JSON-RPC protocol packets
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

    container = Container(settings)
    await container.initialize()

    server = create_mcp_server(container)
    try:
        await server.run_stdio_async()
    finally:
        await container.shutdown()


def run() -> None:
    """Synchronous runner entrypoint."""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    run()
