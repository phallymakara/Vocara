# Vocara Backend Service

The Vocara backend provides the core speech synthesis, voice profile management, key verification, asynchronous task processing, and external protocol integration for the Vocara Voice API Platform.

## Core Capabilities

- Speech Synthesis: Delivers real-time audio streams for interactive requests and orchestrates background job queues for long-form text conversion.
- Voice Profile Management: Coordinates voice catalog listings, language filtering, audio preview delivery, and consent-verified voice cloning workflows.
- Developer Security and Metering: Enforces API key authentication, rate limits, monthly character consumption tracking, and multi-tenant isolation.
- Notification Dispatcher: Delivers signed webhook event notifications with HMAC signatures upon job state changes.
- AI Agent Connectivity: Hosts standardized Model Context Protocol tool and resource endpoints allowing external autonomous assistants and developer tools to interact with speech capabilities.

## Execution Guide

### 1. Environment Setup
Copy the sample environment configuration file:
cp .env.example .env

Set any custom variables in .env (database path, server port, optional Hugging Face API key for ZeroGPU voice cloning).

### 2. Dependency Installation
Prerequisite: Python 3.11 or higher.

Install dependencies using uv:
uv sync

Or install dependencies using standard Python virtual environments:
python -m venv .venv
source .venv/bin/activate (or .venv\Scripts\Activate.ps1 on Windows)
pip install -e .

### 3. Running the API Service
Start the API server using uv:
uv run vocara-api

Or using Python directly:
python -m vocara.main

The server starts on port 8002. Interactive API documentation is available at http://localhost:8002/docs and health status at http://localhost:8002/health.

### 4. Running the Background Queue Worker
For long-form batch audio jobs and asynchronous queue processing, run the worker daemon in a separate terminal:
uv run vocara-worker

Or using Python directly:
python -m vocara.worker

### 5. Automated Verification
Run the backend test suite:
uv run pytest
