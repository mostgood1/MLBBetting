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