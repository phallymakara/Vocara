# Vocara - Voice API Platform

Vocara is a developer-facing Voice API platform designed for speech synthesis, voice cloning, acoustic voice design, and developer integration. It provides a secure, unified interface that allows developers and organizations to integrate voice capabilities into applications and agentic workflows without managing complex infrastructure.

## Platform Capabilities

### 1. Neural Text-to-Speech
Synthesize natural, high-fidelity speech across multiple languages, including Khmer and English. The platform provides real-time streaming audio responses for immediate playback as well as asynchronous job processing for long-form content.

### 2. Consent-Verified Voice Cloning
Create personalized voice profiles from reference audio recordings. The platform enforces explicit consent verification during registration and generates instant preview audio spoken in the cloned voice.

### 3. Acoustic Voice Design
Derive customized voice variations by adjusting pitch, speaking rate, emotional inflections, and expressive styles while preserving original timbre.

### 4. Developer Console and Management
A modern web management interface provides comprehensive developer tools:
- API key provisioning, active session switching, and revocation.
- Real-time text-to-speech studio with in-browser audio player and multi-format export.
- Voice Library management with full voice inspection, editing, and deletion capabilities.
- Live usage metrics and monthly character quota monitoring.
- Asynchronous batch job status tracking and signed webhook endpoint registration.

### 5. Model Context Protocol Integration
Native support for the Model Context Protocol allows AI assistants, autonomous agents, and developer environments to discover available voices, inspect voice metadata, and generate speech directly through standardized tool and resource interfaces.

## Step-by-Step Setup and Execution Guide

Follow the stages below to set up and run the entire Vocara platform locally, from cloning the source code to launching the backend services and developer web console.

### Stage 1: Clone the Repository

Clone the project repository to your local system using your preferred Git client:

git clone https://github.com/phallymakara/Vocara.git

Or if you authenticate using SSH keys:

git clone git@github.com:phallymakara/Vocara.git

Once cloned, navigate into the project root directory:

cd Vocara

### Stage 2: Configure Environment Files

The platform requires environment configurations for both the backend service and the frontend web console.

1. Backend Configuration:
Navigate to the backend directory. Copy the sample environment file to create your active configuration file:
- On Linux and macOS: cp .env.example .env
- On Windows PowerShell: Copy-Item .env.example .env

Open .env in your text editor. The default settings are preconfigured for local development (database file, default port 8002, and local file storage). If you wish to enable cloud-based voice cloning models, add your Hugging Face API token to the HUGGINGFACE_API_KEY variable.

2. Frontend Configuration:
Navigate to the frontend directory. Copy the sample environment file to create your local frontend configuration file:
- On Linux and macOS: cp .env.example .env.local
- On Windows PowerShell: Copy-Item .env.example .env.local

Open .env.local in your text editor and ensure NEXT_PUBLIC_API_BASE_URL is set to your backend API endpoint, such as http://localhost:8002/api/v1.

### Stage 3: Setup and Run the Backend API Service

Prerequisite: Python 3.11 or higher.

1. Navigate to the backend directory:
cd backend

2. Install dependencies:
Using the uv package manager:
uv sync

Alternatively, using standard Python virtual environments:
- On Linux and macOS: python3 -m venv .venv && source .venv/bin/activate && pip install -e .
- On Windows: python -m venv .venv && .venv\Scripts\Activate.ps1 && pip install -e .

3. Start the API service:
Using uv:
uv run vocara-api

Alternatively, using Python directly:
python -m vocara.main

4. Verify the backend is running:
The server will start listening at http://localhost:8002. Open your web browser and navigate to:
- Interactive API Documentation: http://localhost:8002/docs
- Service Health Check: http://localhost:8002/health

Keep this terminal window running to maintain the active backend service.

### Stage 4: Setup and Run the Frontend Developer Console

Prerequisite: Node.js version 18 or higher and npm.

1. Open a new terminal window and navigate to the frontend directory:
cd Vocara/frontend

2. Install Node dependencies:
npm install

3. Start the development server:
npm run dev

4. Verify the frontend is running:
The web console will start on port 3000. Open your web browser and navigate to:
http://localhost:3000

The Vocara Developer Console should now load and connect to your local backend API.

### Stage 5: Run the Background Worker (Optional for Long Batch Tasks)

For processing long-form batch audio jobs and asynchronous queue tasks, run the background worker process.

1. Open another terminal window and navigate to the backend directory:
cd Vocara/backend

2. Start the worker daemon:
Using uv:
uv run vocara-worker

Alternatively, using Python directly:
python -m vocara.worker

The worker will monitor the local queue and execute long-running synthesis jobs in the background.

### Stage 6: First-Time Use and Platform Verification

Once both the backend and frontend are running, you can test the platform features:

1. Provision an API Key:
In the web console, navigate to the API Keys tab. Click to create a new API key (for example, named Development Key). Copy and save your secret key, then select it as the active session key.

2. Test Real-Time Speech Synthesis:
Navigate to the Studio tab. Select a voice profile from the dropdown menu, enter sample text in English or Khmer, and click Generate Speech. Use the embedded audio player to listen to or download the generated audio file.

3. Explore the Voice Library and Voice Cloning:
Navigate to the Voice Library tab to browse available voices and listen to sample previews. To clone a new voice, switch to the Clone Voice tab, enter the voice profile details, upload a clean WAV or MP3 audio reference, confirm the consent declaration, and click Clone Voice. The cloned voice will immediately appear in your library with an automatic voice preview.

## Automated Verification

To run backend test suites and confirm all system components are operating correctly:

cd backend
uv run pytest

To test the frontend production build pipeline:

cd frontend
npm run build
