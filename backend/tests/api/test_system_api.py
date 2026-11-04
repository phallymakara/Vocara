"""API integration tests for system discovery endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_languages_endpoint(async_client: AsyncClient) -> None:
    """GET /api/v1/system/languages returns supported language metadata."""
    resp = await async_client.get("/api/v1/system/languages")
    assert resp.status_code == 200
    languages = resp.json()
    assert isinstance(languages, list)
    assert len(languages) >= 2

    km_lang = next((lang for lang in languages if lang["code"] == "km-KH"), None)
    assert km_lang is not None
    assert km_lang["name"] == "Khmer"
    assert km_lang["is_default"] is True


@pytest.mark.asyncio
async def test_system_formats_endpoint(async_client: AsyncClient) -> None:
    """GET /api/v1/system/formats returns supported audio formats."""
    resp = await async_client.get("/api/v1/system/formats")
    assert resp.status_code == 200
    formats = resp.json()
    assert isinstance(formats, list)

    format_names = [f["format"] for f in formats]
    assert "mp3" in format_names
    assert "wav" in format_names
    assert "flac" in format_names
    assert "ogg" in format_names
