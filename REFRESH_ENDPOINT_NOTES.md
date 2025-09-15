## Pitcher Props Refresh & Enriched Fields

This project now exposes a manual refresh endpoint to force an on-demand update of pitcher prop lines and regenerated recommendations.

### Endpoint
`POST /api/pitcher-props/refresh`

Body (JSON):
```
{ "date": "YYYY-MM-DD" }
```
The date is optional; only respected if it matches the server business date.

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
