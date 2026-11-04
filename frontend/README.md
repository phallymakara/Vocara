# Vocara Developer Web Console

The Vocara frontend provides an interactive, responsive management portal for developers to test speech synthesis, manage custom voice profiles, generate credentials, monitor usage quotas, and manage webhook endpoints.

## User Interface Modules

- Text-to-Speech Studio: Interactive interface for drafting text, choosing voices, tuning speed and format, generating speech in real time, and playing audio directly within the browser.
- Voice Library: Comprehensive catalog of public system voices and private custom voices. Provides tools to preview voice samples, edit metadata, delete custom voices, and clone new voice profiles from reference audio files.
- API Key Management: Secure credentials portal for generating new API tokens, inspecting secret keys, switching active sessions, and revoking deprecated keys.
- Usage and Analytics: Visual metrics dashboard tracking monthly character usage, tier allocations, remaining quotas, and historical consumption.
- Webhooks and Batch Jobs: Diagnostic view displaying asynchronous generation job states, processing logs, and webhook endpoint subscription management.

## Getting Started

### Configuration
Configure the web console API connection by creating your local environment file from the provided template file, specifying the target backend service URL.

### Local Development
To launch the developer console locally, install the package dependencies with your package manager, then run the local development server. The console will become accessible in your web browser.

### Production Build
To prepare optimized, static production assets, execute the standard web application build script. Compiled static files will be placed into the production distribution directory.
