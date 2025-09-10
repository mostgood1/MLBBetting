# Pitcher Prop Modeling Roadmap

This directory will hold data prep, feature extraction, model training, and calibration code for pitcher strikeouts (K) and outs/IP projections.

Modules to be added:
- build_historical_dataset.py
- feature_builder.py
- train_models.py
- variance_model.py
- calibration.py

# Modeling Roadmap (Expanded)

This directory houses the emerging ML pipeline for pitcher prop projections.

## Phase 1: Historical Dataset
- Script: `build_historical_dataset.py` (initial version) aggregates daily starting pitchers, Bovada lines (if captured), season stats, opponent K%, team K%, park factor.
- Next Enhancements:
  - Add realized outcomes (actual strikeouts, outs/IP) after game completion.
  - Capture line movement (open vs close) if multiple snapshots available.
  - Persist implied probabilities from over/under prices.
  - Add line juice (American odds) and convert to fair probability (vig removal) for calibration.

## Phase 2: Feature Enrichment
Add per-start dynamic features:
- Recent form rolling (K%, IP, pitches/start) already partially available elsewhere.
- Opponent platoon (vs L / vs R K%, BB%, wOBA).
- Lineup-level contact metrics (requires projected lineup ingestion).
- Park weather (temp, humidity, wind, roof state) & umpire tendencies.
- Pitch mix deltas vs opponent weaknesses (whiff%, chase%).
- Rest days & travel (distance, time zone changes) heuristics.

## Phase 3: Modeling
Targets:
- Expected strikeouts (mean) & distribution (Negative Binomial parameters r, p or mu, k).
- Expected outs / IP distribution (could approximate via gamma/normal + discrete adjustment or simulate PA sequence).

Approach:
- Gradient Boosted Trees (LightGBM / XGBoost) for mean prediction.
- Auxiliary model for variance (predict log-variance; enforce positivity).
- Calibrate distribution to match empirical tail frequencies (isotonic or Platt-style scaling on CDF buckets).
- Quantile models (pinball loss) for direct line recommendation (e.g., median, 75th percentile).

## Phase 4: Market Integration & Calibration
- Compare model mean vs market line; compute edge probability via modeled distribution.
- Shrink edges based on historical Brier reliability by pitcher cluster & market maturity (open vs close).
- Maintain rolling calibration tables.
- Track realized closing line value (CLV) vs model suggested entry points.

## Phase 5: Automation & Monitoring
- Nightly job updates historical dataset with previous day outcomes.
- Drift detection on feature distributions & error metrics.
- Alerting when model vs market residuals exceed control limits.
- SLA dashboards: data freshness, missing feature counts, model latency.

## File Index
- `build_historical_dataset.py` : Assemble base table (incremental append CSV now; upgrade to Parquet later).
- (Planned) `augment_with_outcomes.py` : Append realized outcomes & derived targets.
- (Planned) `train_pitcher_props.py` : Train model(s) & serialize artifacts.
- (Planned) `evaluate_models.py` : Backtest performance, calibration, CLV metrics.
- (Planned) `feature_checks.py` : Integrity & drift checks.

## Immediate TODO
1. Add actual outcomes ingestion (needs box score / game log per date).
2. Store raw over/under prices & implied probabilities (vig removal logic).
3. Implement LightGBM training script scaffold (`train_pitcher_props.py`).
4. Create evaluation script (`evaluate_models.py`).
5. Add integrity checks (row counts per date, duplicate (date,pitcher) keys).
6. Add Negative Binomial fit utility (method of moments from mean & variance or ML fit on historical).
