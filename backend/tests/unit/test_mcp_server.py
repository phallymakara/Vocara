"""Unit tests for Vocara Model Context Protocol (MCP) server and tools."""

from collections.abc import AsyncGenerator
import json
import os
import shutil
import pytest
from httpx import ASGITransport, AsyncClient

from vocara.container import Container
from vocara.core.config import Settings
from vocara.main import create_app
from vocara.mcp.server import create_mcp_server


@pytest.fixture
async def mcp_container() -> AsyncGenerator[Container, None]:
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./test_mcp.db",
        ENVIRONMENT="development",
        STORAGE_BACKEND="local",
        LOCAL_STORAGE_DIR="./test_storage_mcp",
        INFERENCE_ENGINE_TYPE="fake",
    )
    container = Container(settings)
    await container.initialize()
    try:
        yield container
    finally:
        await container.shutdown()
        if os.path.exists("./test_mcp.db"):
            try:
                os.remove("./test_mcp.db")
            except Exception:
                pass
        if os.path.exists("./test_storage_mcp"):
            try:
                shutil.rmtree("./test_storage_mcp")
            except Exception:
                pass


@pytest.mark.asyncio
async def test_mcp_list_voices_tool(mcp_container: Container) -> None:
    """Verifies that vocara_list_voices tool returns active voices."""
    server = create_mcp_server(mcp_container)

    # Call tool
    res = await server.call_tool("vocara_list_voices", {"language": "all"})
    assert res is not None
    assert not res.is_error

    data = res.structured_content["result"]
    assert len(data) >= 3
    names = [v["name"] for v in data]
    assert any("Sophea" in n for n in names)
    assert any("Dara" in n for n in names)


@pytest.mark.asyncio
async def test_mcp_get_voice_details_tool(mcp_container: Container) -> None:
    """Verifies that vocara_get_voice_details tool returns specific voice attributes."""
    server = create_mcp_server(mcp_container)

    res = await server.call_tool("vocara_get_voice_details", {"voice_id": "voice-sophea-built-in"})
    assert not res.is_error

    voice_data = res.structured_content
    assert voice_data["id"] == "voice-sophea-built-in"
    assert "Sophea" in voice_data["name"]
    assert "language" in voice_data


@pytest.mark.asyncio
async def test_mcp_preview_voice_tool(mcp_container: Container) -> None:
    """Verifies that vocara_preview_voice tool returns base64 audio sample."""
    server = create_mcp_server(mcp_container)

    res = await server.call_tool("vocara_preview_voice", {"voice_id": "voice-dara-built-in"})
    assert not res.is_error

    preview_data = res.structured_content
    assert preview_data["voice_id"] == "voice-dara-built-in"
    assert "audio_base64" in preview_data
    assert len(preview_data["audio_base64"]) > 0


@pytest.mark.asyncio
async def test_mcp_generate_speech_tool(mcp_container: Container) -> None:
    """Verifies that vocara_generate_speech synthesizes audio via MCP."""
    server = create_mcp_server(mcp_container)

    res = await server.call_tool(
        "vocara_generate_speech",
        {
            "text": "Hello world from MCP integration test",
            "voice_id": "voice-sophea-built-in",
            "speed": 1.0,
            "output_format": "mp3",
        },
    )
    assert not res.is_error

    synthesis_data = res.structured_content
    assert synthesis_data["status"] == "completed"
    assert "audio_base64" in synthesis_data
    assert synthesis_data["duration_seconds"] > 0
    assert synthesis_data["characters_used"] > 0


@pytest.mark.asyncio
async def test_mcp_catalog_resource(mcp_container: Container) -> None:
    """Verifies that vocara://voices/catalog returns live JSON string of voices."""
    server = create_mcp_server(mcp_container)

    # Read resource
    resource_contents = await server.read_resource("vocara://voices/catalog")
    assert resource_contents is not None
    assert len(resource_contents) > 0
    # Parse json
    catalog_list = json.loads(resource_contents[0].content)
    assert isinstance(catalog_list, list)
    assert len(catalog_list) >= 3


@pytest.mark.asyncio
async def test_mcp_sse_route_integration(test_settings: Settings) -> None:
    """Verifies /mcp endpoints are mounted and enforce authentication."""
    # Testing environment enforces 401 Unauthorized without credentials
    app = create_app(test_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp_unauth = await client.post(
                "/mcp/messages/",
                headers={"X-API-Key": "voc_invalid_key"},
            )
            assert resp_unauth.status_code == 401
            assert resp_unauth.json()["error"]["code"] == "UNAUTHORIZED"

            # In testing mode without key, it strictly requires auth (401)
            resp_no_key = await client.post("/mcp/messages/")
            assert resp_no_key.status_code == 401

    # Development environment allows fallback developer session
    dev_settings = test_settings.model_copy(update={"ENVIRONMENT": "development"})
    app_dev = create_app(dev_settings)
    async with app_dev.router.lifespan_context(app_dev):
        transport_dev = ASGITransport(app=app_dev)
        async with AsyncClient(transport=transport_dev, base_url="http://test") as client_dev:
            resp_dev = await client_dev.post("/mcp/messages/")
            # Reaches Starlette SSE transport handler (status 400 for missing session/payload)
            assert resp_dev.status_code == 400
