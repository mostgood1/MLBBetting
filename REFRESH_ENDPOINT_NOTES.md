## Pitcher Props Refresh & Enriched Fields

This project now exposes a manual refresh endpoint to force an on-demand update of pitcher prop lines and regenerated recommendations.

### Endpoint
`POST /api/pitcher-props/refresh`

Body (JSON):
```
{ "date": "YYYY-MM-DD", "push": true }
```
The date is optional; only respected if it matches the server business date.
If `push` is true and push is enabled by environment flags (see below), the server
will attempt to add, commit, and push updated files for today under `data/daily_bovada/`.

### Response
```
{
  success: true|false,
  date: "2025-09-15",
  duration_sec: 3.41,
  results: { fetch_props: true, generate_recommendations: true },
  errors: [],
  message: "Refreshed"
}
```

### Rate Limiting & Security
* A 30s in-process cooldown prevents spamming. During cooldown the endpoint returns **429** with a JSON error.
* If environment variable `PITCHER_REFRESH_TOKEN` is set, callers must supply header `X-Refresh-Token: <value>` or they receive **401**.

### Enabling Git Push (optional)
Push behavior is controlled entirely by environment variables and is safe to leave disabled.

Required to enable push (any one):
- `PITCHER_GIT_PUSH_ENABLED=1` (preferred)
- or `AUTO_GIT_PUSH_ENABLED=1`

To explicitly disable regardless of the above:
- `AUTO_GIT_PUSH_DISABLED=1`

Optional identity configuration (recommended on platforms without a default git identity):
- `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`
- `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`

Optional remote override:
- `GIT_PUSH_URL` (HTTPS URL with token or SSH URL). If set, a temporary remote `push-tmp` is used for push.

### Unified Pitcher Props Enrichment
Objects in `/api/pitcher-props/unified` now include in each `plays` (primary play) bundle when available:
* `kelly_fraction` – raw Kelly (0–1). Multiply by bankroll for recommended wager; apply your own cap.
* `selected_ev` – Expected value probability delta for the selected side (fraction). Displayed on the UI as a percent.
* `over_odds` / `under_odds` – Current American odds associated with the market.

### Frontend Additions
Pitcher card header shows: primary play (side/stat/line), K odds badge, Kelly %, EV %, and a `stale` tag when any lines are inherited from an earlier snapshot that day.

Legend explains edge color thresholds and arrow semantics (▲ Over / ▼ Under) plus stale meaning.

### Testing
`tests/test_pitcher_props_refresh.py` performs a smoke sequence: unified -> refresh -> unified, validates structural keys and optional enriched metrics.

### Notes
* Refresh is synchronous and depends on upstream Bovada + local projection code; allow several seconds.
* If odds are temporarily absent, recommendations may be empty; refresh again later or wait for automated pipeline.

---

## Render / Cron Wiring

There are two supported ways to run refresh in production (e.g., Render):

### Option A) HTTP cron hits the endpoint
- Configure a cron job (Render Cron or any scheduler) to POST to:
  - `https://<your-host>/api/pitcher-props/refresh` with JSON `{ "push": true }`
- Headers:
  - `Content-Type: application/json`
  - If you set `PITCHER_REFRESH_TOKEN` on the server, add `X-Refresh-Token: <value>`
- Environment on the app service (if you want auto-push):
  - `PITCHER_GIT_PUSH_ENABLED=1`
  - Optional: `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`
  - Optional: `GIT_PUSH_URL` (e.g., `https://<token>@github.com/<owner>/<repo>.git`)

Pros: Simple; leverages the running web app. Cons: The request blocks until refresh finishes (a few seconds).

### Option B) Background worker runs the script
- Add a Background Worker service that runs:
  - `python scripts/refresh_pitcher_props_and_push.py`
- Set the same env flags as above for push behavior.
- The script returns exit code 0 on success, 1 on failure, and prints a JSON summary including `git_push` details.

Pros: Decouples from web request lifecycle; easier to schedule frequent runs. Cons: Another service to manage.

### Scheduling tips
- Early day: run every 10–15 minutes until lines stabilize. Midday: reduce to every 20–30 minutes. Adjust to taste.
- Respect the built-in 30s cooldown on the HTTP endpoint if you use Option A.

### Troubleshooting
- Hit `GET /api/health/unified-meta` to confirm today’s props and last-known files exist and their sizes.
- Hit `GET /api/props/spotlight-health` to see Spotlight counts, source date, and whether the UI is using synthesized or stale data.
- Check server logs for lines like `refresh_bovada_pitcher_props` and `generate_pitcher_prop_projections` results.

