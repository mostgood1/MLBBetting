Historical Pitcher Prop Dataset
--------------------------------
File: pitcher_props_history.csv

Each row: one pitcher appearance (projected start) and associated sportsbook lines + adjusted projection factors for strikeouts and outs (where lines available).

Primary key (current): date + pitcher_id. If a pitcher appears twice same date (doubleheader), this will need augmentation with game_id.

Columns summary:
- line_*: sportsbook main line (may be empty if no market)
- proj_*: raw projection before contextual adjustments
- adj_*: adjusted projection including opponent K-rate, park factor, recent form, patience outs factor
- diff_*: raw projection minus line
- diff_adj_*: adjusted projection minus line
- edge_dir_*: simple directional recommendation from current rule-based engine
- *_odds_*: over/under American odds from sportsbook market

Next extensions (planned):
- Add final outcomes (actual strikeouts, outs recorded) once box score ingestion added
- Add variance estimates (modeled sigma or NB dispersion)
- Add lineup-handedness K% features
- Weather / roof / umpire fields
- Pitch mix deltas & whiff metrics

Regeneration: Script historical_pitcher_prop_dataset.py appends new rows without duplicating existing (date,pitcher_id).

Backfill strategy: accumulate daily going forward; optional retro-scrape if past daily feature JSONs/lines retained.