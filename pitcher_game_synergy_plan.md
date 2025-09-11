Pitcher -> Game Model Synergy Plan
=================================
Goal: Inject richer pitcher distribution intelligence into game simulation & betting engines for improved side/total/derivative accuracy.

Current Pitcher Layer Artifacts
--------------------------------
1. Point projections per market (outs, strikeouts, earned_runs, hits_allowed, walks).
2. Dynamic standard deviation per market (volatility + calibration).
3. Opponent-adjusted rates (strength factor applied to K rate, ERA, WHIP components).
4. Line movement-derived volatility (EW variance on line changes).

Enhancement Objectives
----------------------
A. Generate parametric distributions for key pitcher outputs (Outs ~ Normal/Truncated, Ks ~ Poisson or Normal, ER ~ Poisson/Gamma, Hits ~ Poisson) using calibrated stds.
B. Feed sampled or moment-based summaries into game run expectancy logic (affects: bullpen exposure timing, opponent scoring distribution, total run probability, first 5 inning markets).
C. Update game simulation each time pitcher projection volatility meaningfully changes (trigger thresholds on std delta or line movement events).
D. Persist per-pitcher distribution snapshots for reproducibility & auditing.
E. Provide synergy metrics (delta in win prob / total runs after latest pitcher distribution update) via a monitoring endpoint.

Data Flow Integration Points
----------------------------
1. Distribution Builder (new module: pitcher_distributions.py)
   - Input: master pitcher stats + opponent strength + calibration + volatility.
   - Output: dict per pitcher: {
       outs: {mean, std, dist:'normal', p_ge_18, p_ge_21,...},
       strikeouts: {lambda or mean/std},
       earned_runs: {lambda or shape/scale},
       hits_allowed: {lambda},
       walks: {lambda}
     }
2. Game Simulation Injection
   - Replace static pitcher expected innings / runs allowed with distribution-aware expectation and variance.
   - Adjust bullpen inning share (less expected outs -> earlier bullpen usage -> shift team run allowed distribution).
   - Recompute team run expectancy via existing or new run model using: expected_earned_runs, variance, opponent offensive index.
3. Recommendation Engine Hook
   - When generating side/total recommendations, incorporate updated variance; widen confidence intervals -> more selective picks.
4. Trigger Logic
   - Subscribe to broadcast_pitcher_update events; if event.market in ('outs','earned_runs','strikeouts') AND absolute(line_delta) >= threshold OR volatility var updated over X% -> rebuild that pitcher's distribution + refresh affected games.

Algorithm Sketches
------------------
Outs Distribution:
  mean = outs_proj, std = calibrated_std_outs; use truncated normal at [0, 27]; derive P(>=k outs) via CDF complement.
Strikeouts:
  Option 1: Normal(mean, std from mapping of outs std + K rate variance)
  Option 2: Poisson(lambda = projected Ks); choose Poisson until lambda > 10 then normal approximation.
Earned Runs:
  Use Gamma(k, theta) with mean=proj_ER and variance derived from calibration or historical ERA dispersion. Solve k = (mean^2)/var.
Hits/Walks:
  Poisson with lambda = projection (cap lambda>=0.2). Variance = lambda.

Distribution Persistence
------------------------
File: data/daily_bovada/pitcher_prop_distributions_<DATE>.json
  {"date":"YYYY-MM-DD","pitchers": {key: {...above...}}}

Game Model Usage
----------------
1. For each game, compute opposing pitcher ER distribution -> expected runs allowed early innings.
2. Combine with bullpen run allowance model (existing or heuristic: bullpen_runs_mean = f(bullpen ERA, innings = 9 - outs_mean/3)).
3. Aggregate to team runs allowed distribution (convolution approx Normal using combined mean & variance from pitcher+bullpen).
4. Recompute win probability using run differential distribution (existing simulation or pythagorean with adjusted RS, RA).

Metrics / Endpoint
------------------
Add endpoint /api/pitcher-game-synergy providing per-game delta snapshot:
  { game_id, pitcher, prev_win_prob, new_win_prob, delta, prev_total_mean, new_total_mean, timestamp }

Implementation Phases
---------------------
Phase 1: Module + file persistence + manual trigger script.
Phase 2: Auto trigger from SSE broadcast events (line_move) with threshold logic.
Phase 3: Integrate into game recommendation pipeline.
Phase 4: Add synergy endpoint + UI panel.
Phase 5: Calibrate distribution forms (compare vs. realized outcomes) -> refine shape choices.

Next Step Minimal Code
----------------------
1. Create pitcher_distributions.py with build_distributions(date) writing snapshot file.
2. Hook into continuous updater after generate_props_main() to refresh distributions (lightweight call) when changed_any.
3. Add synergy placeholder endpoint returning last distribution build timestamp + count pitchers covered.

This plan document generated automatically. Proceed to implement Phase 1 when approved.
