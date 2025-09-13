# Pitcher Props Modeling Workflow

Quick steps to refresh models using realized outcomes:

1) Build base dataset from daily projection features:
   - python historical_pitcher_prop_dataset.py

2) Append realized outcomes as training targets:
   - python -m training.augment_with_outcomes

3) Train models (uses realized targets when present):
   - python -m training.train_pitcher_models

Artifacts will be saved under models/pitcher_props/<version>/ with per-market models and DictVectorizers for consistent runtime features.

Notes:
- If realized outcomes are missing for some rows, trainer falls back to proj_* columns.
- Runtime (pitcher_model_runtime.py) automatically loads the latest model bundle.

## Nightly automation (Windows)

Use Task Scheduler to run nightly after games finish:

1) Open Task Scheduler → Create Task
2) Triggers → New… → Daily at 2:30 AM (adjust for your timezone)
3) Actions → New… → Program/script:
   - Program: powershell.exe
   - Arguments: -ExecutionPolicy Bypass -File "C:\Users\mostg\OneDrive\Coding\MLB-Betting\nightly_model_refresh.ps1"
   - Start in: C:\Users\mostg\OneDrive\Coding\MLB-Betting
4) Conditions: Uncheck "Start the task only if the computer is on AC power" if needed
5) OK

Logs will be written as nightly_model_refresh_YYYYMMDD_HHMMSS.log in the repo root.