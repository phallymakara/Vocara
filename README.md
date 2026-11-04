# Vocara - Voice API Platform

Vocara is a developer-facing Voice API platform for text-to-speech (TTS), consent-verified voice cloning, voice variation design, and voice library management. It provides a unified, secure interface allowing developers to integrate speech capabilities into products without hosting voice AI infrastructure.

## Project Structure

```text
Vocara/
├── backend/                  # Python FastAPI Backend
│   ├── src/vocara/           # Hexagonal application source
│   ├── migrations/           # Alembic database migrations
│   ├── tests/                # Pytest unit, integration, and API test suites
│   ├── worker/               # Background queue worker
│   ├── pyproject.toml        # Backend dependencies and CLI entrypoints
│   ├── Dockerfile            # Container build
│   └── .env.example          # Backend configuration template
├── frontend/                 # React 19 + TypeScript + Vite Web Console
│   ├── src/                  # Components, pages, typed API client
│   ├── package.json          # Frontend dependencies
│   └── vite.config.ts        # Vite configuration and proxy
├── docker-compose.yml        # Multi-container local deployment
└── Makefile                  # Task automation shortcuts
```

## Prerequisites

- Python >= 3.11
- uv >= 0.4.0
- Node.js >= 20.0.0
- npm >= 10.0.0

## Quick Start

### 1. Start the Backend API

```bash
cd backend
uv sync --all-extras
uv run vocara
```

The backend API server will start at `http://127.0.0.1:8002`. Interactive documentation is available at `http://127.0.0.1:8002/docs`.

### 2. Start the Frontend Console

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend web console will be accessible at `http://localhost:3000`.

### 3. Start the Background Worker (Optional for long-form speech)

```bash
cd backend
uv run vocara-worker
```

## Model Context Protocol (MCP) Integration

Vocara provides native Model Context Protocol (MCP) server support, allowing external AI assistants (Cursor IDE, Claude Desktop, autonomous LLM agents) and external developer services to discover voices and synthesize speech directly.

### Connection Transports

Vocara supports two MCP transports:

1. **Remote SSE Transport (Recommended)**: For network-accessible agents, web services, and Cursor IDE.
   - Endpoint: `http://localhost:8002/mcp/sse?api_key=voc_YOUR_API_KEY`
   - Messages: `http://localhost:8002/mcp/messages/`
2. **Local Stdio Transport**: For Claude Desktop running as a local command.
   - Command: `uv run vocara-mcp` inside `backend/`

---

### Client Configuration

#### 1. Cursor IDE (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "vocara": {
      "url": "http://localhost:8002/mcp/sse?api_key=voc_YOUR_API_KEY"
    }
  }
}
```

#### 2. Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vocara": {
      "command": "uv",
      "args": [
        "--directory",
        "<path-to-vocara>/backend",
        "run",
        "vocara-mcp"
      ],
      "env": {
        "VOCARA_API_KEY": "voc_YOUR_API_KEY"
      }
    }
  }
}
```

#### 3. Python Client (`mcp` library)

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    url = "http://localhost:8002/mcp/sse?api_key=voc_YOUR_API_KEY"
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Discover available voices
            voices = await session.call_tool("vocara_list_voices", {"language": "km"})
            print("Voices:", voices)

            # 2. Synthesize speech
            result = await session.call_tool("vocara_generate_speech", {
                "text": "សួស្តីពិភពលោក",
                "voice_id": "voice-sophea-built-in",
                "output_format": "mp3"
            })
            print("Synthesis result:", result)

asyncio.run(main())
```

#### 4. TypeScript / Node Client (`@modelcontextprotocol/sdk`)

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
  const transport = new SSEClientTransport(
    new URL("http://localhost:8002/mcp/sse?api_key=voc_YOUR_API_KEY")
  );

  const client = new Client(
    { name: "vocara-agent", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  // List voices
  const voices = await client.callTool({
    name: "vocara_list_voices",
    arguments: { language: "all" },
  });
  console.log("Vocara voices:", voices);
}

main().catch(console.error);
```

---

### Exposed MCP Tools & Resources

| Name | Type | Description | Key Parameters |
| :--- | :--- | :--- | :--- |
| `vocara_list_voices` | Tool | List all accessible voices (built-in, designed, cloned) | `language` (e.g. `'km'`, `'en'`, `'all'`), `voice_type` |
| `vocara_get_voice_details` | Tool | Retrieve full metadata and acoustic modifiers for a voice | `voice_id` (string) |
| `vocara_preview_voice` | Tool | Retrieve base64-encoded WAV audio preview sample | `voice_id` (string) |
| `vocara_generate_speech` | Tool | Synthesize text into high-fidelity neural speech | `text`, `voice_id`, `speed` (default 1.0), `output_format` (`mp3`/`wav`) |
| `vocara://voices/catalog` | Resource | Dynamic live JSON catalog of all available voices | URI resource |

---

## Running Tests

Execute test suite inside the backend directory:

```bash
cd backend
uv run pytest
```

Execute frontend build check:

```bash
cd frontend
npm run build
```
