"""Vocara Model Context Protocol (MCP) server implementation.

Exposes Vocara voice catalog, audio preview, and speech synthesis capabilities
to external developers, IDEs, and AI assistants.
"""

import base64
import json
from contextvars import ContextVar
from typing import Any

from mcp.server.mcpserver import MCPServer

from vocara.container import Container
from vocara.core.logging import get_logger
from vocara.domain.constants import DEFAULT_PREVIEW_TEXT
from vocara.domain.entities import ApiKey, Voice
from vocara.domain.enums import AudioFormat, VoiceType

logger = get_logger("vocara.mcp")

# Context variable holding the active authenticated ApiKey for the current MCP session
current_mcp_key_ctx: ContextVar[ApiKey | None] = ContextVar("current_mcp_key_ctx", default=None)


def _format_voice_dict(voice: Voice) -> dict[str, Any]:
    """Format domain Voice entity into a clean MCP dictionary."""
    voice_type_val = (
        voice.voice_type.value
        if hasattr(voice.voice_type, "value")
        else str(voice.voice_type)
    )
    return {
        "id": voice.id,
        "name": voice.name,
        "language": voice.language,
        "voice_type": voice_type_val,
        "description": voice.description,
        "pitch": voice.modifiers.get("pitch", 1.0),
        "speed": voice.modifiers.get("speed", 1.0),
        "emotion": voice.modifiers.get("emotion"),
        "style": voice.modifiers.get("style"),
        "preview_url": f"/api/v1/voices/{voice.id}/preview",
    }


def create_mcp_server(container: Container) -> MCPServer:
    """Create and configure the Vocara MCP Server instance with tools and resources."""
    server = MCPServer(
        name="vocara-voices",
        description="Vocara Neural Voice & Speech Synthesis MCP Provider",
        version="0.1.0",
    )

    async def _resolve_api_key(session: Any) -> ApiKey:
        """Resolve caller's authenticated API key or fallback to dev key."""
        active_key = current_mcp_key_ctx.get()
        if active_key is not None:
            return active_key
        auth_service = container.get_auth_service(session)
        return await auth_service.get_or_create_dev_key()

    @server.tool(
        name="vocara_list_voices",
        description=(
            "List all accessible speech synthesis voices available in Vocara. "
            "Filter by language (e.g. 'km-KH', 'en', 'all') or voice type ('built_in', 'designed', 'cloned')."
        ),
    )
    async def list_voices(
        language: str = "all",
        voice_type: str = "all",
    ) -> list[dict[str, Any]]:
        """List voices available to the current user."""
        if not container.session_factory:
            return []

        async with container.session_factory() as session:
            api_key = await _resolve_api_key(session)
            voice_service = container.get_voice_service(session)

            lang_filter = None if language.lower() in ("all", "") else language
            type_filter = None
            if voice_type.lower() in ("built_in", "designed", "cloned"):
                type_filter = VoiceType(voice_type.lower())

            voices = await voice_service.list_voices(
                owner_id=api_key.owner_id,
                language=lang_filter,
                voice_type=type_filter,
                limit=100,
            )
            return [_format_voice_dict(v) for v in voices]

    @server.tool(
        name="vocara_get_voice_details",
        description="Retrieve complete metadata, acoustic modifiers, and description for a specific voice ID.",
    )
    async def get_voice_details(voice_id: str) -> dict[str, Any]:
        """Fetch details of a specific voice."""
        if not container.session_factory:
            return {"error": "Database session factory not initialized"}

        async with container.session_factory() as session:
            api_key = await _resolve_api_key(session)
            voice_service = container.get_voice_service(session)
            try:
                voice = await voice_service.get_voice_by_id(voice_id, owner_id=api_key.owner_id)
                return _format_voice_dict(voice)
            except Exception as err:
                return {"error": str(err), "voice_id": voice_id}

    @server.tool(
        name="vocara_preview_voice",
        description="Retrieve an audio preview sample for a given voice ID speaking 'សួស្តីខ្ញុំជាវូការាជាអេអាយបម្លែងអក្សរទៅជាសម្លេង' (returns base64 WAV audio).",
    )
    async def preview_voice(voice_id: str) -> dict[str, Any]:
        """Return preview audio bytes for a voice speaking the canonical preview phrase."""
        if not container.session_factory:
            return {"error": "Database session factory not initialized"}

        async with container.session_factory() as session:
            api_key = await _resolve_api_key(session)
            voice_service = container.get_voice_service(session)
            try:
                audio_bytes, content_type = await voice_service.get_preview_stream(
                    voice_id, owner_id=api_key.owner_id
                )
                return {
                    "voice_id": voice_id,
                    "preview_text": DEFAULT_PREVIEW_TEXT,
                    "content_type": content_type,
                    "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                    "preview_url": f"/api/v1/voices/{voice_id}/preview",
                }
            except Exception as err:
                return {"error": str(err), "voice_id": voice_id}

    @server.tool(
        name="vocara_generate_speech",
        description=(
            "Synthesize text into natural human speech using any Vocara voice. "
            "Returns base64 encoded audio bytes, duration in seconds, and billed characters."
        ),
    )
    async def generate_speech(
        text: str,
        voice_id: str,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: str = "mp3",
    ) -> dict[str, Any]:
        """Synthesize script text using a selected voice."""
        if not container.session_factory:
            return {"error": "Database session factory not initialized"}

        fmt_enum = AudioFormat.MP3 if output_format.lower() == "mp3" else AudioFormat.WAV

        async with container.session_factory() as session:
            api_key = await _resolve_api_key(session)
            tts_service = container.get_tts_service(session)

            try:
                audio_bytes, duration, format_str, job = await tts_service.synthesize_or_enqueue(
                    api_key=api_key,
                    text=text,
                    voice_id=voice_id,
                    language=language,
                    speed=speed,
                    output_format=fmt_enum,
                )

                if audio_bytes is not None:
                    return {
                        "status": "completed",
                        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                        "duration_seconds": duration,
                        "format": format_str,
                        "characters_used": len(text),
                        "voice_id": voice_id,
                    }

                if job is not None:
                    return {
                        "status": "queued_async",
                        "job_id": job.id,
                        "characters_used": len(text),
                        "message": "Long-form text (>250 chars) queued for batch background synthesis.",
                        "result_url": f"/api/v1/jobs/{job.id}/result",
                    }

                return {"error": "Synthesis yielded no audio output"}

            except Exception as err:
                logger.error("mcp_synthesis_failed", error=str(err), voice_id=voice_id)
                return {"error": str(err), "voice_id": voice_id}

    @server.resource(
        "vocara://voices/catalog",
        name="Vocara Live Voice Directory",
        description="Real-time directory of available neural voices in Vocara.",
        mime_type="application/json",
    )
    async def voices_catalog_resource() -> str:
        """Provide voice catalog as a context resource."""
        if not container.session_factory:
            return "[]"

        async with container.session_factory() as session:
            api_key = await _resolve_api_key(session)
            voice_service = container.get_voice_service(session)
            voices = await voice_service.list_voices(owner_id=api_key.owner_id, limit=50)
            return json.dumps([_format_voice_dict(v) for v in voices], indent=2)

    return server
