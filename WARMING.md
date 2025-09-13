# Service Warming Guide

This project includes warmers to reduce first-hit latency and keep key pages (home, betting guidance) snappy.

## Endpoints warmed
- /api/today-games/quick (fast home snapshot)
- /api/live-status (lightweight live/schedule cache)
- /api/kelly-betting-guidance (drives /betting-guidance)
- /api/betting-guidance/performance (historical perf summary)
- /api/pitcher-props/unified (only in full warm)
- /api/today-games (full, heavier; only in full warm)

## Startup warmer (automatic)
On app boot, a background thread warms:
- /api/pitcher-props/unified?date=<business date>
- /api/live-status?date=<business date>
- /api/today-games?date=<business date>
- /api/today-games/quick?date=<business date>
- /api/kelly-betting-guidance
- /api/betting-guidance/performance

No action needed—this reduces cold starts after deploy.

## Manual warm endpoint
- Quick-only (lightweight):
  GET /api/warm?async=1&quick_only=1
- Full warm (heavier):
  GET /api/warm (optionally add ?async=1)

The JSON response includes per-step durations and ok flags.

## Periodic warmer (optional, env-gated)
Enable a built-in background loop with environment variables:
- ENABLE_PERIODIC_WARM=1
- PERIODIC_WARM_INTERVAL_SECONDS=480  # optional, default 480s (8 min)

Behavior:
- Every cycle warms: quick snapshot, live status, betting guidance APIs
- Every 3rd cycle also warms: pitcher props unified and full today-games

## Platform cron/uptime pings (recommended)
If your platform supports cron/uptime pings (e.g., Render cron job), schedule:
- Method: GET
- URL: https://<your-domain>/api/warm?async=1&quick_only=1
- Interval: 5–10 minutes

This keeps home and betting guidance pages warm without heavy work.

## Verification
- Check quick snapshot: GET /api/today-games/quick?date=YYYY-MM-DD
- Warm all and inspect steps: GET /api/warm (no async)
- Betting guidance health: GET /api/kelly-betting-guidance and /api/betting-guidance/performance

## Notes
- The home UI already passes `date` to both quick and full endpoints.
- Quick-only warm is safe to run frequently; run full warm less often if needed.
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
