# Vocara Backend Service

Vocara is a developer-facing Voice API platform providing real-time and asynchronous text-to-speech (TTS), consent-verified voice cloning, voice variation design, and voice library management.

## Architecture

Built using Hexagonal Architecture (Ports and Adapters):
- `src/vocara/domain`: Pure entities, enums, and port interfaces.
- `src/vocara/services`: Core use-case coordination.
- `src/vocara/infrastructure`: Database, storage, queue, and inference adapters.
- `src/vocara/api`: FastAPI HTTP routes, middleware, and request/response validation.
- `src/vocara/worker`: Background queue worker daemon.

## Local Execution

Install dependencies:
```bash
uv sync --all-extras
```

Start the API service:
```bash
uv run vocara
```

Start the background worker:
```bash
uv run vocara-worker
```

Execute tests:
```bash
uv run pytest
```

