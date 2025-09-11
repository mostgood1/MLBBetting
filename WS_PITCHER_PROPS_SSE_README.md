# Pitcher Props Real-Time Streaming & Line History

## Overview
Added three predictive enhancements:
1. Opponent-adjusted pitcher prop projections (K rate, ERA, WHIP adjustments via team Elo-derived strength from `enhanced_features.json`).
2. Historical line movement logging: every change in line or odds per pitcher/market appended to `data/daily_bovada/pitcher_prop_line_history_<DATE>.json`.
3. Server-Sent Events (SSE) endpoint for push-style updates (`/api/pitcher-props/stream`) plus REST history endpoint (`/api/pitcher-props/line-history?date=YYYY-MM-DD`).

## Files & Key Additions
- `continuous_pitcher_props_updater.py`
  * Detects line & odds changes; writes events with timestamps.
  * File: `pitcher_prop_line_history_<DATE>.json` (structure: `{date, events:[...]}`).
- `generate_pitcher_prop_projections.py`
  * Opponent context loaded from `enhanced_features.json` (team Elo -> strength scalar).
  * Adjusts K rate (-) and ERA/WHIP (+) for strong lineups; inverse for weak lineups.
  * Adds `opponent_strength` field in each recommendation.
- `app.py`
  * `/api/pitcher-props/line-history` returns last 500 events for date.
  * `/api/pitcher-props/stream` provides SSE stream (subscribe via EventSource in JS).

## Consuming the Stream (Frontend JS Snippet)
```js
const es = new EventSource('/api/pitcher-props/stream');
es.onmessage = (evt) => {
  const data = JSON.parse(evt.data);
  // data will mirror broadcast payloads (extend broadcast_pitcher_update when wiring)
  console.log('Pitcher prop update', data);
};
```

## Broadcasting Updates
Currently the updater logs history but does not yet broadcast each event automatically. To enable live pushes, you can:
1. Import `broadcast_pitcher_update` in `continuous_pitcher_props_updater.py` (guard import errors) and call it after detecting `line_events`.
2. Or schedule a lightweight poller in `app.py` to tail the history file and push deltas.

Example (optional) insertion after `if line_events:` block:
```python
try:
    from app import broadcast_pitcher_update  # ensure import safe if module name differs in prod
    for ev in line_events[-10:]:  # limit burst size
        broadcast_pitcher_update({'type': 'line_move', **ev})
except Exception:
    pass
```

## Data Model (Line Event)
```json
{
  "ts": "2025-09-11T13:45:12.345Z",
  "pitcher": "gerrit cole",
  "market": "strikeouts",
  "old_line": 6.5,
  "new_line": 7.0,
  "old_over_odds": "+105",
  "new_over_odds": "+100",
  "old_under_odds": "-135",
  "new_under_odds": "-120"
}
```

## Opponent Strength Scalar
`strength = (elo - 1500)/400` bounded to [-1,1]. Applied as:
- K rate *= (1 - 0.12 * strength)
- ERA *= (1 + 0.18 * strength)
- WHIP *= (1 + 0.10 * strength)

These coefficients are heuristic and should be refined with backtesting.

## Volatility & Probability Calibration
A lightweight exponential variance model now updates per pitcher/market on each detected line move (`pitcher_prop_volatility.json`). This feeds dynamic standard deviations in probability estimation, refining p_over and EV.

Structure:
```json
{
  "gerrit cole": {
    "strikeouts": {"var": 0.72, "updates": 5},
    "outs": {"var": 1.10, "updates": 3}
  }
}
```
`var` is an exponentially weighted variance of absolute line changes. Std dev = sqrt(var) bounded [0.4, 3.5].

## Realized Results (Scaffolding)
Placeholder files planned: `pitcher_prop_realized_results.json` for future calibration of model vs. outcomes to rebalance variance and opponent coefficients.

## Next Refinements (Suggestions)
- Integrate broadcast into updater (as shown) for immediate front-end updates.
- Add rolling volatility model for dynamic STD_FACTORS by pitcher & market.
- Persist realized results to measure calibration of opponent adjustments.
- Introduce decay (recent 30 days weighting) for opponent strength separate from Elo.

## Safety & Backwards Compatibility
- If `enhanced_features.json` absent, opponent adjustments gracefully no-op.
- SSE endpoint is additive; existing APIs unchanged.
- History file grows through the day; prune or compress post-day if desired.

---
Generated automatically.
