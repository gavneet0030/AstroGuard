# AstroGuard Mission Control — Phase 6

## Requirements
- Node.js 20 or newer (tested in this environment with Node 24)
- npm
- AstroGuard backend running separately

## Setup
```powershell
Copy-Item .env.example .env.local
npm install
npm run typecheck
npm test
npm run lint
npm run build
npm run dev
```

Open http://localhost:3000.

## Verified API integrations
The dashboard checks only:
- `GET /health`
- `GET /ready`
- `GET /api/v1/system/database/health`

Configure the base URL with `NEXT_PUBLIC_ASTROGUARD_API_BASE_URL`.

## Intentionally unconnected screens
Telemetry, anomaly, investigation and model data remain placeholders until backend
route prefixes, response schemas, pagination and access-control requirements have
been confirmed. Placeholder values use an em dash and are not fabricated metrics.

## Security
- No credentials are collected.
- No authentication is simulated.
- No write endpoint is called.
- Never put private keys or secrets in `NEXT_PUBLIC_*` variables.

## Acceptance boundary
A successful production build does not prove browser-level acceptance or backend
integration. Manually open each route and inspect the browser console and network
panel. Verify the API base URL and CORS configuration.
