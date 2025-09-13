API warmers and cold-start mitigation

Overview
- Added a dedicated /api/warm endpoint to prebuild critical caches on demand.
- Enhanced startup warmer to also prebuild the ultra-fast /api/today-games/quick snapshot.
- Optional periodic warmer thread, disabled by default and controlled via env vars.

Endpoints
- GET /api/warm
  - Query params:
    - date: YYYY-MM-DD (defaults to business date)
    - async=1: run in background and return immediately
    - quick_only=1: warm only quick snapshot + live status (skip heavier routes)
  - Returns: JSON with per-step timings, success flags, and total_duration_ms.

What gets warmed
- Quick snapshot: /api/today-games/quick
- Live status: /api/live-status
- Unified props (unless quick_only=1): /api/pitcher-props/unified
- Full today games (unless quick_only=1): /api/today-games

Startup warmer
- On boot, the app now warms:
  - /api/pitcher-props/unified
  - /api/live-status
  - /api/today-games
  - /api/today-games/quick (new)

Optional periodic warmer
- Disabled by default. Enable with env:
  - ENABLE_PERIODIC_WARM=1
  - PERIODIC_WARM_INTERVAL_SECONDS=480   # optional; default 480s (8 minutes)
- Behavior: runs continuously in a background thread; every 3rd cycle performs a full warm, otherwise quick-only.

Render setup suggestions
- Set Health Check Path to /healthz.
- Keep at least 1 min instance if possible to reduce cold starts.
- Add a Cron Job or external ping to /api/warm?async=1&quick_only=1 every 5–10 minutes (and optionally once per hour without quick_only to fully warm).

Local quick tests (PowerShell)
- Invoke-WebRequest -UseBasicParsing "http://localhost:5000/api/warm?quick_only=1" | Select-Object -ExpandProperty Content
- Invoke-WebRequest -UseBasicParsing "http://localhost:5000/api/warm?async=1" | Select-Object -ExpandProperty Content
- Invoke-WebRequest -UseBasicParsing "http://localhost:5000/api/today-games/quick" | Select-Object -ExpandProperty Content

Notes
- All API responses include no-store/no-cache headers for speed and freshness.
- Server-Timing and X-Response-Time headers are attached for observability.
