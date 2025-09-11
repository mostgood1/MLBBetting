Pitcher Props Diagnostics & Streaming
=====================================

Added Components
----------------
1. /api/pitcher-props/model-diagnostics – aggregates volatility, calibration, realized outcomes and recommendation coverage.
2. /api/pitcher-props/line-history – returns recent intraday line movement events (limit=500 default).
3. /api/pitcher-props/stream – Server-Sent Events feed (line_move + heartbeat + future event types).
4. backfill_pitcher_prop_realized_outcomes.py – retroactively populates realized outcomes + recalibration.
5. static/pitcher_props_sse_demo.js – small frontend helper to visualize streaming events & top volatility.

Quick Usage
-----------
Frontend demo (in a template):
  <div id="pitcher-sse"></div>
  <script src="/static/pitcher_props_sse_demo.js"></script>
  <script>initPitcherPropsSSE('pitcher-sse');</script>

Backfill historical outcomes (e.g. last 45 days):
  python backfill_pitcher_prop_realized_outcomes.py --days 45

Or explicit date range:
  python backfill_pitcher_prop_realized_outcomes.py --start 2025-08-10 --end 2025-09-10

Diagnostics Sample:
  curl http://localhost:5000/api/pitcher-props/model-diagnostics | jq '.coverage,.calibration.markets.strikeouts'

Event Payload Types
-------------------
Current broadcast (line_move):
  {"type":"line_move","ts":ISO_TS,"pitcher":"name_key","market":"strikeouts","old_line":x,"new_line":y,...}

Heartbeat every ~30s to keep the stream alive:
  {"type":"heartbeat","ts":ISO_TS}

Extending
---------
Add new broadcast types by calling broadcast_pitcher_update({...}) in generators.
Include `proj_update`, `volatility_update`, etc. as needed. Frontend auto-renders text lines.

Calibration Flow
----------------
1. Backfill script populates pitcher_prop_realized_results.json.
2. Script recomputes avg absolute error per market => suggested_std.
3. continuous updater or projection script can read calibration meta to override STD factors.

Volatility
----------
Line movement deltas update an EW variance; sqrt(var) ~ dynamic std cap [0.4,3.5].
Displayed in diagnostics & demo script (top 10 by std).

Next Ideas
----------
1. Add probability calibration visualization (qq style bins) to diagnostics endpoint.
2. Persist per-pitcher market performance (HIT/MISS counts) surface for selective trust weighting.
3. Feed refined outs/ER distributions into game simulation to adjust team run expectancy.

---
File created automatically.