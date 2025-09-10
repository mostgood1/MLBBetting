# Bovada Props: Refresh, Monitor, and Sync

This repo captures Bovada pitcher prop lines daily to power reconciliation and the UI.

## One-off refetch (today or chosen date)

- Refetch and write `data/daily_bovada/bovada_pitcher_props_YYYY_MM_DD.json`:
  - python tools/refetch_bovada_props.py --git-commit
  - Optional: `--date YYYY-MM-DD`

- Rebuild pitcher projections (force) so `/api/today-games` exposes lines immediately:
  - python tools/rebuild_pitcher_projections.py --git-commit

## Ongoing monitoring

- Check coverage vs starters and refetch if coverage < 75%:
  - python tools/monitor_bovada_props.py --min-cover 0.75 --git-commit

- Windows Task Scheduler: run `tools/schedule_bovada_checks.ps1` every 15 minutes from 10:00–23:59 US/Eastern.

## Files written

- data/daily_bovada/bovada_pitcher_props_YYYY_MM_DD.json
- data/daily_bovada/pitcher_projections_update_YYYY_MM_DD.json
- data/daily_bovada/matching_report_YYYY_MM_DD.json
- data/daily_bovada/projection_features_YYYY_MM_DD.json
- data/daily_bovada/adjustment_summary_YYYY_MM_DD.json
- data/daily_bovada/pitcher_validation_YYYY_MM_DD.json

## Notes

- Name matching uses accent-insensitive normalization. If specific starters routinely miss, add aliases in the normalizer.
- The API route `/api/today-games` pulls from the projections snapshots. Rebuild projections after refetch to expose new lines.
- Scripts support `--git-commit` to ensure local data and the GitHub repo stay aligned.
