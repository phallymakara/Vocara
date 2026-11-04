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

## Getting Started

### Configuration
Template configuration files are provided in the backend and frontend directories. To configure your local instance:
- Copy the backend environment template file to create your active backend configuration, and set your desired database, storage, and service parameters.
- Copy the frontend environment template file to configure the web console API connection endpoint.

### Backend Application Service
To run the API service, navigate to the backend directory, install the required dependencies using the environment manager, and start the Vocara service. The service provides interactive documentation through standard web browser endpoints upon startup.

### Frontend Web Console
To launch the developer console, navigate to the frontend directory, install the web dependencies, and start the development server. The console will be accessible through your local browser.

### Background Worker Service
For processing large text documents and asynchronous speech generation tasks, the background worker daemon can be launched alongside the main API server.

### Quality and Verification
Automated test suites covering unit logic, repository access, service coordination, and API endpoints are maintained in the backend directory. Frontend production assets can be verified by executing the standard web build pipeline.
