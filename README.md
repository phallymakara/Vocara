# Vocara

Vocara is a developer-facing Voice API platform for text-to-speech (TTS), consent-verified voice cloning, voice variation design, and voice library management. It provides a unified, secure interface allowing developers to integrate speech capabilities into products without hosting voice AI infrastructure.

## Core Capabilities

- Text-to-Speech (TTS): Dynamic routing between real-time streaming (< 250 chars) and asynchronous background processing (>= 250 chars).
- Voice Cloning: High-fidelity voice replication from audio samples with mandatory explicit consent confirmation.
- Voice Variation Design: Derive customized voice profiles (adjusting pitch, speed, emotion, style) starting from existing base voices.
- Voice Library Management: Multi-tenant voice catalog supporting built-in public voices and developer private voices.
- Developer Access: API key lifecycle management, per-key usage tracking, rate limiting, and monthly quotas.
- Asynchronous Background Worker: Dedicated queue worker processing speech synthesis tasks, uploading audio artifacts, and dispatching signed webhooks.
- Developer Webhooks: Cryptographically signed (HMAC-SHA256) event delivery for job status notifications.
- System Discovery: Catalogs for supported languages and audio formats.

## System Architecture

Vocara adheres to Hexagonal Architecture (Ports and Adapters) and Object-Oriented design principles:

- Domain (`src/vocara/domain`): Pure business logic entities, enumerations, and Protocol interfaces (Ports). Contains zero framework dependencies.
- Services (`src/vocara/services`): Use-case business logic coordinating repositories, storage, and inference adapters through ports.
- Infrastructure (`src/vocara/infrastructure`): Concrete adapters implementing domain ports:
  - Database: PostgreSQL with SQLAlchemy 2 (async) and generic BaseRepository.
  - Storage: Local filesystem, Azure Blob Storage, and Cloudflare R2 / S3.
  - Inference: VoxCPM serverless adapter (Modal) and local fake engine for zero-cost testing.
  - Queue: Redis-backed task queue with in-memory fallback for asynchronous jobs.
- API Layer (`src/vocara/api`): FastAPI HTTP endpoints, request/response validation schemas, and middlewares.
- Worker (`src/vocara/worker`): Background task consumer executing long-form synthesis jobs and sending webhooks.

## Prerequisites

- Python >= 3.11
- uv >= 0.4.0
- Docker and Docker Compose (for PostgreSQL and Redis services)

## Getting Started

### 1. Environment Setup

Clone the repository and create your local environment file:

```bash
cp .env.example .env
```

Review `.env` and adjust database credentials, storage backend, or logging options as needed.

### 2. Dependency Installation

Sync all project dependencies and virtual environment using uv:

```bash
uv sync --all-extras
```

### 3. Start Backing Services

Start local PostgreSQL and Redis containers:

```bash
docker-compose up -d postgres redis
```

Run database schema migrations:

```bash
uv run alembic upgrade head
```

### 4. Run Application

Start the Vocara API server:

```bash
uv run vocara
```

Start the Vocara background inference worker:

```bash
uv run vocara-worker
```

The API service starts on `http://0.0.0.0:8000`. When `DEBUG=true`, interactive documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## REST API Reference

All protected endpoints accept authentication via `Authorization: Bearer <api_key>` or `X-API-Key: <api_key>`.

### Authentication and Keys

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/keys` | Create a developer API key (returns raw key once) |
| GET | `/api/v1/keys` | List active developer API keys |
| DELETE | `/api/v1/keys/{key_id}` | Revoke an API key |

### Usage Metering

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/usage` | Retrieve monthly character quota and consumption stats |

### Voice Library and Audio

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/voices` | List accessible built-in and private voices |
| GET | `/api/v1/voices/{id}` | Get voice profile details |
| PATCH | `/api/v1/voices/{id}` | Update custom voice metadata |
| DELETE | `/api/v1/voices/{id}` | Soft-delete a custom voice |
| GET | `/api/v1/voices/{id}/preview` | Stream sample preview audio |
| POST | `/api/v1/voices/clone` | Clone a voice (requires audio file and consent confirmation) |
| POST | `/api/v1/voices/design` | Create a derivative voice variation from a base voice |

### Speech Synthesis and Jobs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/tts` | Convert text to speech (200 stream for < 250 chars, 202 job for >= 250 chars) |
| GET | `/api/v1/jobs` | List recent speech generation jobs |
| GET | `/api/v1/jobs/{id}` | Check job status (queued, processing, completed, failed) |
| GET | `/api/v1/jobs/{id}/result` | Download synthesized audio result |

### Webhooks

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/webhooks` | Register a webhook callback URL |
| GET | `/api/v1/webhooks` | List registered webhook subscriptions |
| DELETE | `/api/v1/webhooks/{id}` | Revoke a webhook subscription |

### System Discovery

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/system/languages` | List supported languages and voice counts |
| GET | `/api/v1/system/formats` | List audio formats and encoding specifications |

## Development and Verification

Execute testing, linting, and quality verification tasks via `uv`:

- Run Test Suite:
  ```bash
  uv run pytest
  ```

- Run Linter:
  ```bash
  uv run ruff check src/ tests/
  ```

- Run Code Formatting Check:
  ```bash
  uv run ruff format --check src/ tests/
  ```

- Static Type Checking:
  ```bash
  uv run mypy src/
  ```

## Project Structure

```text
Vocara/
├── .github/
│   └── workflows/
│       └── ci.yml                    # Automated GitHub Actions CI pipeline
├── migrations/                       # Alembic schema migrations
├── src/vocara/
│   ├── main.py                       # App factory create_app() and run() entrypoint
│   ├── container.py                  # Single Composition Root (dependency wiring)
│   ├── core/                         # Config, logging, security, domain errors
│   ├── domain/                       # Pure entities, enums, and Protocol ports
│   ├── services/                     # Application business logic services
│   ├── infrastructure/               # Database, storage, queue, and inference adapters
│   ├── api/                          # Endpoints, schemas, dependencies, middlewares
│   ├── worker/                       # Background queue worker process and handler
│   └── utils/                        # Audio validation, normalization, and tone generator
├── tests/
│   ├── api/                          # API endpoint integration test suites
│   ├── integration/                  # Database repository and worker pipeline tests
│   └── unit/                         # Domain service, utility, and adapter unit tests
├── pyproject.toml                    # Package definition and script commands
├── docker-compose.yml                # Local services orchestration (API, worker, db, redis)
├── Dockerfile                        # Production container build
├── Makefile                          # Task runner shortcuts
└── .env.example                      # Configuration template
```
