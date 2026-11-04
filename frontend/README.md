# Vocara Frontend Web Console

Vocara Frontend is a modern developer web console for managing voice synthesis, voice cloning, API keys, usage quotas, and webhook subscriptions.

## Architecture

The frontend follows a strict Model-View-Controller (MVC) directory structure and manual shadcn/ui installation standards:

```text
frontend/src/
├── models/                     # Data Models & DTO TypeScript interfaces
│   └── types.ts                # Voice, Job, Usage, Webhook, and API key entities
├── controllers/                # Business Logic & State Controllers (Custom Hooks)
│   ├── apiClient.ts            # Centralized HTTP client with dynamic URLs and error parsing
│   ├── useTTSController.ts     # Speech synthesis orchestration and job polling
│   ├── useVoiceController.ts   # Voice listing, preview playback, cloning, and design
│   ├── useKeyController.ts     # API key generation, revocation, and active selection
│   ├── useUsageController.ts   # Monthly quota calculation and metrics
│   └── useWebhookController.ts # Webhook subscription management and job inspection
├── views/                      # UI Presentation Components
│   ├── components/             # Reusable UI views
│   │   ├── ui/                 # Official shadcn/ui manual primitives (button, input, dialog, etc.)
│   │   ├── Sidebar.tsx         # Navigation sidebar (brand name auto-hidden on mobile)
│   │   ├── Header.tsx          # Health indicator and active key status
│   │   └── AudioPlayer.tsx     # Flat HTML5 audio playback and seek bar
│   └── pages/                  # Page Views
│       ├── TTSStudioPage.tsx   # Text-to-speech studio
│       ├── VoiceLibraryPage.tsx# Voice catalog, clone, and design modals
│       ├── ApiKeysPage.tsx     # Key generation and table view
│       ├── UsageMetricsPage.tsx# Quota usage and consumption metrics
│       └── WebhooksJobsPage.tsx# Job inspector and webhook registration
├── lib/
│   └── utils.ts                # Tailwind cn() class merge utility
├── App.tsx                     # Top-level view shell
├── main.tsx                    # Entry point mounting root component
└── index.css                   # Global styles, shadcn CSS variables, zero-shadow rules
```

## UI and Engineering Guidelines

- Zero Shadows: Box-shadows are strictly disabled (`box-shadow: none !important;`).
- In-Place Error Handling: Errors appear directly below the affected input with a red border and plain red text.
- No Filled Container Backgrounds: Layout maintains clean flat borders without heavy background fills.
- Mobile Responsive: On mobile viewports, the product brand name is hidden, displaying only the brand logo.
- Dynamic Configuration: API URLs are loaded dynamically via `VITE_API_BASE_URL` with a local relative proxy fallback (`/api/v1`).
- Standard Icons: Uses clean Lucide React icons across all views.

## Development

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

