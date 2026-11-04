# Vocara

> High-fidelity neural text-to-speech, consent-verified voice cloning, and AI agent voice integration platform.

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

---

## Table of Contents

- [About](#about)
- [Key Features](#key-features)
- [Prerequisites & Tech Stack](#prerequisites--tech-stack)
- [Installation](#installation)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Backend Setup & Run](#2-backend-setup--run)
  - [3. Frontend Setup & Run](#3-frontend-setup--run)
  - [4. Background Worker (Optional)](#4-background-worker-optional)
- [Usage & Examples](#usage--examples)
  - [Synthesize Speech via cURL](#synthesize-speech-via-curl)
  - [Synthesize Speech via Python](#synthesize-speech-via-python)
  - [Run the Model Context Protocol (MCP) Server](#run-the-model-context-protocol-mcp-server)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Contact & Acknowledgements](#contact--acknowledgements)

---

## About

Vocara is an open-source, developer-facing Voice API platform designed to simplify the generation, customization, and management of synthetic voices. It bridges the gap between state-of-the-art neural speech models and production applications by providing:

- Unified developer APIs for real-time streaming audio and batch synthesis.
- Multi-language support with specialized support for languages including Khmer and English.
- Consent-verified voice cloning workflows ensuring responsible AI usage.
- Native Model Context Protocol (MCP) tools enabling AI agents and assistants (Claude, Cursor, custom agents) to generate voice natively.
- An interactive developer web management console with an audio studio, API key lifecycle management, voice library CRUD, and usage analytics.

---

## Key Features

- Neural Text-to-Speech: Low-latency streaming audio generation in WAV, MP3, and OGG formats.
- Consent-Verified Voice Cloning: Create custom voice profiles from reference audio files with instant preview generation.
- Acoustic Voice Design: Fine-tune pitch, rate, emotion, and vocal style parameters.
- Voice Library Management: Full create, read, update, and delete (CRUD) capabilities for custom voice profiles.
- Developer Console: Web-based studio for immediate auditioning, quota monitoring, and API key provisioning.
- MCP Server Integration: Direct tool and resource discovery for AI coding assistants and autonomous agents.
- Resilient Architecture: Automatic fallback mechanisms between cloud ZeroGPU inference spaces and local fallback engines.

---

## Prerequisites & Tech Stack

### Prerequisites
- Python: Version 3.11 or higher
- Node.js: Version 18.0.0 or higher
- Package Managers: `uv` (recommended) or `pip` for Python; `npm` for Node.js
- Git: Version 2.30 or higher

### Tech Stack
- Backend: FastAPI, SQLAlchemy 2.0 (asyncio), Pydantic v2, Structlog, Edge-TTS, Hugging Face Gradio Client
- Frontend: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide React
- Protocols: REST API, Server-Sent Events (SSE), Model Context Protocol (MCP)
- Storage: SQLite (local development) / PostgreSQL (production), Local file storage / S3

---

## Installation

### 1. Clone Repository

Clone the project from GitHub and navigate to the root directory:

```bash
git clone https://github.com/phallymakara/Vocara.git
cd Vocara
```

---

### 2. Backend Setup & Run

Open a terminal window for the backend service:

**Windows (PowerShell):**
```powershell
cd backend
Copy-Item .env.example .env
uv sync
uv run vocara-api
```

*(Alternative with standard pip):*
```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m vocara.main
```

**macOS / Linux (Bash):**
```bash
cd backend
cp .env.example .env
uv sync
uv run vocara-api
```

*(Alternative with standard pip):*
```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m vocara.main
```

Once running, the backend service is available at:
- API Base: `http://localhost:8002`
- Interactive Swagger Documentation: `http://localhost:8002/docs`
- Health Check: `http://localhost:8002/health`

---

### 3. Frontend Setup & Run

Open a second terminal window for the web console:

**Windows (PowerShell):**
```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

**macOS / Linux (Bash):**
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Once running, open your browser and navigate to:
- Developer Web Console: `http://localhost:3000`

---

### 4. Background Worker (Optional)

If processing long-form batch synthesis jobs or asynchronous webhook deliveries, run the worker daemon in a third terminal:

**Windows (PowerShell):**
```powershell
cd backend
uv run vocara-worker
```

**macOS / Linux (Bash):**
```bash
cd backend
uv run vocara-worker
```

---

## Usage & Examples

### Synthesize Speech via cURL

Generate an audio stream directly from the command line:

```bash
curl -X POST "http://localhost:8002/api/v1/tts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: voc_live_your_api_key_here" \
  -d '{
    "text": "Hello, welcome to Vocara Voice API Platform.",
    "voice_id": "km-KH-PisethNeural",
    "speed": 1.0,
    "format": "mp3"
  }' \
  --output output.mp3
```

---

### Synthesize Speech via Python

```python
import httpx

API_URL = "http://localhost:8002/api/v1/tts"
API_KEY = "voc_live_your_api_key_here"

payload = {
    "text": "Welcome to Vocara speech synthesis.",
    "voice_id": "en-US-JennyNeural",
    "speed": 1.0,
    "format": "mp3"
}

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

with httpx.Client(timeout=30.0) as client:
    response = client.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()
    with open("synthesized_audio.mp3", "wb") as f:
        f.write(response.content)

print("Audio saved successfully to synthesized_audio.mp3")
```

---

### Run the Model Context Protocol (MCP) Server

Vocara can be integrated directly into MCP-compatible clients such as Claude Desktop or Cursor:

```bash
cd backend
uv run vocara-mcp
```

MCP Configuration for Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vocara": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/Vocara/backend",
        "run",
        "vocara-mcp"
      ]
    }
  }
}
```

---

## Testing

Run the automated backend test suite covering API endpoints, repositories, services, and MCP tools:

```bash
cd backend
uv run pytest
```

Verify frontend compilation and type checking:

```bash
cd frontend
npm run build
```

---

## Contributing

Contributions from the developer community are welcome. To contribute:

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add support for custom audio format"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request detailing the changes, motivation, and test coverage.

Please ensure all tests pass and code conforms to project styling (`uv run ruff check .` and `npm run lint`) prior to submitting.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete details.

---

## Contact & Acknowledgements

### Maintainer
- Makara Phally - [GitHub Profile](https://github.com/phallymakara)

### Acknowledgements
- [FastAPI](https://fastapi.tiangolo.com/) for the modern, high-performance web framework.
- [Next.js](https://nextjs.org/) for the developer console frontend interface.
- [Edge-TTS](https://github.com/rany2/edge-tts) for high-quality speech synthesis capabilities.
- [Model Context Protocol](https://modelcontextprotocol.io/) for standardizing agentic AI tool interactions.
- [Hugging Face](https://huggingface.co/) for open model ecosystems and ZeroGPU infrastructure.
