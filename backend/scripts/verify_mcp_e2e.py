"""End-to-End verification script for Vocara Model Context Protocol (MCP) service.

Connects to the live running Vocara server over HTTP/SSE, validates the JSON-RPC
protocol handshake, lists tools, executes voice discovery and speech synthesis,
and verifies authentication boundaries.
"""

import asyncio
import sys
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client


async def verify_mcp_e2e() -> bool:
    server_base = "http://127.0.0.1:8002"
    sse_url = f"{server_base}/mcp/sse"

    print(f"--- 1. Testing Server Availability ({server_base}) ---")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{server_base}/api/v1/voices", timeout=5.0)
            if resp.status_code != 200:
                print(f"[FAIL] Server responded with status {resp.status_code}")
                return False
            print(f"[PASS] Server is online and healthy (Status {resp.status_code})")
        except Exception as e:
            print(f"[FAIL] Could not connect to Vocara server: {e}")
            return False

        print("\n--- 2. Testing Authentication Rejection with Invalid Key ---")
        unauth_resp = await client.post(
            f"{server_base}/mcp/messages/",
            headers={"X-API-Key": "voc_invalid_secret_key"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            timeout=5.0,
        )
        if unauth_resp.status_code == 401:
            print("[PASS] Unauthorized request rejected with HTTP 401 (as expected)")
        else:
            print(f"[FAIL] Expected HTTP 401 but received {unauth_resp.status_code}")
            return False

    print("\n--- 3. Connecting to MCP SSE Transport & Initializing Session ---")
    try:
        async with sse_client(sse_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                init_result = await session.initialize()
                print(f"[PASS] MCP Handshake successful. Server: {init_result.server_info.name} (v{init_result.server_info.version})")

                print("\n--- 4. Listing Registered MCP Tools ---")
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print(f"Registered tools ({len(tool_names)}): {', '.join(tool_names)}")
                expected_tools = [
                    "vocara_list_voices",
                    "vocara_get_voice_details",
                    "vocara_preview_voice",
                    "vocara_generate_speech",
                ]
                for exp in expected_tools:
                    assert exp in tool_names, f"Missing expected tool: {exp}"
                print("[PASS] All required MCP tools are registered")

                print("\n--- 5. Executing 'vocara_list_voices' Tool ---")
                voices_res = await session.call_tool("vocara_list_voices", {"language": "all"})
                assert not voices_res.is_error, "Tool call returned an error"
                voices_data = voices_res.structured_content.get("result", [])
                print(f"[PASS] Retrieved {len(voices_data)} voices:")
                for v in voices_data:
                    print(f"  - {v['name']} ({v['id']}) [{v['language']}]")

                print("\n--- 6. Executing 'vocara_get_voice_details' Tool ---")
                detail_res = await session.call_tool(
                    "vocara_get_voice_details",
                    {"voice_id": "voice-sophea-built-in"},
                )
                assert not detail_res.is_error
                detail_data = detail_res.structured_content
                print(f"[PASS] Voice Details for {detail_data['id']}:")
                print(f"  Name: {detail_data['name']}")
                print(f"  Pitch: {detail_data['pitch']}, Speed: {detail_data['speed']}")

                print("\n--- 7. Executing 'vocara_generate_speech' Tool ---")
                tts_res = await session.call_tool(
                    "vocara_generate_speech",
                    {
                        "text": "Hello from Vocara live MCP end-to-end verification.",
                        "voice_id": "voice-sophea-built-in",
                        "speed": 1.0,
                        "output_format": "mp3",
                    },
                )
                assert not tts_res.is_error
                tts_data = tts_res.structured_content
                print(f"[PASS] Speech Synthesis Successful:")
                print(f"  Status: {tts_data.get('status')}")
                print(f"  Duration: {tts_data.get('duration_seconds')}s")
                print(f"  Characters: {tts_data.get('characters_used')}")
                print(f"  Audio Payload Size: {len(tts_data.get('audio_base64', ''))} chars (Base64)")

                print("\n=======================================================")
                print("   ALL MCP END-TO-END VERIFICATION CHECKS PASSED!     ")
                print("=======================================================")
                return True

    except Exception as e:
        print(f"[FAIL] MCP Error during live session: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_mcp_e2e())
    sys.exit(0 if success else 1)

