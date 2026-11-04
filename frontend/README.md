# Vocara Developer Web Console

The Vocara frontend provides an interactive, responsive management portal for developers to test speech synthesis, manage custom voice profiles, generate credentials, monitor usage quotas, and manage webhook endpoints.

## User Interface Modules

- Text-to-Speech Studio: Interactive interface for drafting text, choosing voices, tuning speed and format, generating speech in real time, and playing audio directly within the browser.
- Voice Library: Comprehensive catalog of public system voices and private custom voices. Provides tools to preview voice samples, edit metadata, delete custom voices, and clone new voice profiles from reference audio files.
- API Key Management: Secure credentials portal for generating new API tokens, inspecting secret keys, switching active sessions, and revoking deprecated keys.
- Usage and Analytics: Visual metrics dashboard tracking monthly character usage, tier allocations, remaining quotas, and historical consumption.
- Webhooks and Batch Jobs: Diagnostic view displaying asynchronous generation job states, processing logs, and webhook endpoint subscription management.

## Execution Guide

### 1. Environment Setup
Copy the sample environment configuration file:
cp .env.example .env.local

Verify that NEXT_PUBLIC_API_BASE_URL points to your running backend API instance, for example http://localhost:8002/api/v1.

### 2. Dependency Installation
Prerequisite: Node.js version 18 or higher and npm.

Install dependencies from the frontend directory:
npm install

### 3. Running the Development Server
Launch the local web server:
npm run dev

The web console will become available at http://localhost:3000 in your browser.

### 4. Production Build Verification
To verify the production compilation:
npm run build
