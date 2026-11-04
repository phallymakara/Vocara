# Vocara Backend Service

The Vocara backend provides the core speech synthesis, voice profile management, key verification, asynchronous task processing, and external protocol integration for the Vocara Voice API Platform.

## Core Services

- Speech Synthesis: Delivers real-time audio streams for interactive requests and orchestrates background job queues for long-form text conversion.
- Voice Profile Management: Coordinates voice catalog listings, language filtering, audio preview delivery, and consent-verified voice cloning workflows.
- Developer Security and Metering: Enforces API key authentication, rate limits, monthly character consumption tracking, and multi-tenant isolation.
- Notification Dispatcher: Delivers signed webhook event notifications with HMAC signatures upon job state changes.
- AI Agent Connectivity: Hosts standardized tool and resource endpoints allowing external autonomous assistants and developer tools to interact with speech capabilities.

## Getting Started

### Configuration
Configure your service parameters by setting up the backend environment file based on the provided template file. Supported configurations include database connection URLs, object storage providers, inference engines, and quota thresholds.

### Service Execution
Install the backend dependencies using the project environment manager, then launch the primary service executable. Once running, the service automatically publishes interactive API documentation accessible via your browser.

### Background Queue Processing
When handling batch synthesis operations, start the background worker process. The worker continuously monitors the task queue and processes dispatched audio jobs asynchronously.

### Automated Testing
Comprehensive test coverage is maintained across API routes, business logic, storage adapters, and integration workflows. Tests can be run through the backend environment test command.
