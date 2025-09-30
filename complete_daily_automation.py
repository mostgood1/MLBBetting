#!/usr/bin/env python3
"""
Complete Daily MLB Automation Trigger
Comprehensive script to set up a new day's data from scratch
"""

import os
import sys
import subprocess
import logging
import shutil
from datetime import datetime
from pathlib import Path
import json

def setup_logging():
    """Setup logging for the automation"""
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"complete_daily_automation_{today}.log"
    
    # Create UTF-8 safe stream handler to avoid console encoding errors on Windows
    class Utf8StreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                # Prefer binary write to avoid encoding issues
                try:
                    stream.buffer.write((msg + self.terminator).encode('utf-8', errors='replace'))
                except Exception:
                    # Fallback to text write
                    stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = Utf8StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler]
    )
    
    return logging.getLogger(__name__)

def run_script(script_path: Path, description: str, logger, timeout: int = 300):
    """Run a script with error handling"""
    try:
        logger.info(f"🚀 {description}")
        # If running in no-games mode, skip heavy script execution quickly
        if os.environ.get('NO_GAMES_MODE', '').lower() in ('1', 'true', 'yes'):
            logger.info(f"⏭️ Skipping in no-games mode: {description}")
            return True
        # Ensure script exists before attempting to run
        if not script_path.exists():
            logger.warning(f"⚠️ Script not found, skipping: {script_path}")
            return False

        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=timeout, cwd=str(script_path.parent))
        
        if result.returncode == 0:
            logger.info(f"✅ SUCCESS: {description}")
            if result.stdout and result.stdout.strip():
                # Show last few lines of output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-3:]:  # Show last 3 lines
                    if line.strip():
                        logger.info(f"   {line}")
            return True
        else:
            logger.error(f"❌ FAILED: {description}")
            logger.error(f"Return code: {result.returncode}")
            if result.stderr and result.stderr.strip():
                logger.error(f"Error output: {result.stderr.strip()}")
            if result.stdout and result.stdout.strip():
                logger.error(f"Standard output: {result.stdout.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ TIMEOUT: {description} (>{timeout}s)")
        return False
    except Exception as e:
        logger.error(f"💥 EXCEPTION: {description} - {str(e)}")
        return False

def copy_file_safe(source: Path, target: Path, logger):
    """Safely copy a file with error handling"""
    try:
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(source, target)
            except shutil.SameFileError:
                logger.info(f"SKIP: Source and target are the same file: {source}")
                return True
            logger.info(f"📋 Copied {source.name} to {target}")
            return True
        else:
            logger.warning(f"⚠️  Source file not found: {source}")
            return False
    except Exception as e:
        logger.error(f"❌ Error copying {source} to {target}: {e}")
        return False

# ===== Helpers for days with no games =====
def count_games_in_file(games_path: Path) -> int:
    """Return number of games in a games file (supports list or {"games": [...]})"""
    try:
        if not games_path.exists() or games_path.stat().st_size == 0:
            return 0
        with open(games_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            if isinstance(data.get('games'), list):
                return len(data.get('games') or [])
            if isinstance(data.get('games'), dict):
                return len(data.get('games'))
        return 0
    except Exception:
        return 0

def write_no_games_day_files(data_dir: Path, today: str, today_underscore: str, logger) -> None:
    """Create skeletal files for a no-games day so downstream steps remain stable."""
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        # games file
        games_path = data_dir / f"games_{today}.json"
        if not games_path.exists():
            with open(games_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info(f"🧘 Wrote no-games skeleton: {games_path.name}")
        # betting recommendations
        recs_path = data_dir / f"betting_recommendations_{today_underscore}.json"
        if not recs_path.exists():
            with open(recs_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "date": today,
                    "games": {},
                    "value_bets": [],
                    "notes": "No MLB games today"
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"🧘 Wrote no-games skeleton: {recs_path.name}")
        # real betting lines
        lines_path = data_dir / f"real_betting_lines_{today_underscore}.json"
        if not lines_path.exists():
            with open(lines_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "date": today,
                    "lines": {},
                    "notes": "No MLB games today"
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"🧘 Wrote no-games skeleton: {lines_path.name}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to write no-games skeleton files: {e}")

def seed_no_games_unified_cache(unified_cache_path: Path, today: str, games_path: Path, recs_path: Path, logger) -> None:
    """Seed unified_predictions_cache.json with a no-games entry for today."""
    try:
        cache = {}
        if unified_cache_path.exists() and unified_cache_path.stat().st_size > 0:
            try:
                with open(unified_cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f) or {}
            except Exception:
                cache = {}
        cache.setdefault('predictions_by_date', {})
        cache['predictions_by_date'][today] = {
            'games': {},
            'timestamp': datetime.now().isoformat(),
            'total_games': 0,
            'source': 'no_games',
            'games_file': str(games_path),
            'betting_file': str(recs_path),
            'notes': 'No MLB games today'
        }
        unified_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(unified_cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"🧘 Seeded unified cache with no-games entry: {unified_cache_path.name}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to seed unified cache for no-games day: {e}")

def complete_daily_automation():
    """Run the complete daily automation workflow"""
    logger = setup_logging()
    today = datetime.now().strftime('%Y-%m-%d')
    today_underscore = today.replace('-', '_')
    
    logger.info("=" * 80)
    logger.info("🏆 COMPLETE DAILY MLB AUTOMATION STARTING")
    logger.info(f"📅 Date: {today}")
    logger.info("=" * 80)
    
    # Base directory setup (repo root)
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    mlb_betting_data_dir = data_dir

    # Ensure OddsAPI key is available to downstream scripts (from ENV or local secrets)
    try:
        if not os.environ.get('ODDS_API_KEY'):
            secrets_dir = base_dir / 'secrets'
            key_file = secrets_dir / 'odds_api_key'
            if key_file.exists():
                with open(key_file, 'r', encoding='utf-8') as f:
                    key_val = f.read().strip()
                if key_val:
                    os.environ['ODDS_API_KEY'] = key_val
                    logger.info('🔐 Loaded ODDS_API_KEY from local secrets file')
            else:
                # Optional: check config file as last resort
                cfg_path = data_dir / 'closing_lines_config.json'
                if cfg_path.exists():
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as cf:
                            cfg = json.load(cf) or {}
                        api_keys = cfg.get('api_keys') or {}
                        key_val = api_keys.get('odds_api_key') or api_keys.get('the_odds_api_key')
                        if key_val:
                            os.environ['ODDS_API_KEY'] = key_val
                            logger.info('🔐 Loaded ODDS_API_KEY from config file')
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"ENV key bootstrap skipped: {e}")
    
    # Pre-check: Verify which scripts are available
    logger.info("\n🔍 PRE-CHECK: Verifying Available Scripts")
    scripts_to_check = [
        "fetch_today_games.py",
        "enhanced_mlb_fetcher.py", 
        "fetch_todays_starters.py",
        "weather_park_integration.py",
        "fast_pitcher_updater.py",
        "fetch_bovada_pitcher_props.py",            # NEW pitcher props lines
        "generate_pitcher_prop_projections.py",     # NEW pitcher prop projections
        "weekly_team_updater.py", 
        "daily_data_updater.py",
        "fetch_betting_lines_simple.py",       # DraftKings-specific fetcher
        "fetch_betting_lines_real.py",
        "integrated_closing_lines.py",
        "daily_ultrafastengine_predictions.py",
        "unified_betting_engine.py",
        "betting_recommendations_engine.py"
    ]
    
    available_scripts = []
    for script in scripts_to_check:
        script_path = base_dir / script
        if script_path.exists():
            available_scripts.append(script)
            logger.info(f"  ✅ {script}")
        else:
            logger.warning(f"  ❌ {script} - NOT FOUND")
    
    logger.info(f"📊 Found {len(available_scripts)}/{len(scripts_to_check)} scripts")
    
    if len(available_scripts) < 3:
        logger.warning("⚠️ Missing critical scripts - automation may fail")
    else:
        logger.info("✅ Sufficient scripts available for automation")
    
    # Step 1: Fetch Today's Games & Schedule 
    logger.info("\n🎯 STEP 1: Fetching Today's MLB Games & Schedule")
    games_candidates = [
        base_dir / "fetch_today_games.py",
        base_dir / "enhanced_mlb_fetcher.py"
    ]

    success1 = False
    for candidate in games_candidates:
        if candidate.exists():
            success1 = run_script(candidate, f"Fetch Today's Games ({candidate.name})", logger, 300)
            if success1:
                break
        else:
            logger.debug(f"Games fetch candidate not found: {candidate}")

    if not success1:
        logger.warning("⚠️ No games fetch script found - continuing with existing data")
    
    # Detect a no-games day and switch to light mode
    no_games_day = False
    try:
        games_path_for_check = data_dir / f"games_{today}.json"
        games_count = count_games_in_file(games_path_for_check)
        if games_count == 0:
            no_games_day = True
            logger.info("🧘 No MLB games today detected. Enabling no-games mode and skipping heavy steps.")
            # Ensure skeletal files exist for today
            write_no_games_day_files(data_dir, today, today_underscore, logger)
            # Seed unified cache so the frontend has a stable entry
            unified_cache_seed_path = data_dir / "unified_predictions_cache.json"
            recs_seed_path = data_dir / f"betting_recommendations_{today_underscore}.json"
            seed_no_games_unified_cache(unified_cache_seed_path, today, games_path_for_check, recs_seed_path, logger)
            # Signal run_script to skip subsequent heavy invocations
            os.environ['NO_GAMES_MODE'] = '1'
    except Exception as e:
        logger.debug(f"No-games detection failed gracefully: {e}")
    
    # Step 2: Fetch Probable Pitchers
    logger.info("\n🎯 STEP 2: Fetching Probable Pitchers")
    pitcher_candidates = [
        base_dir / "fetch_todays_starters.py"
    ]

    success2 = False
    for candidate in pitcher_candidates:
        if candidate.exists():
            success2 = run_script(candidate, f"Fetch Probable Pitchers ({candidate.name})", logger, 300)
            if success2:
                break
        else:
            logger.debug(f"Pitcher fetch candidate not found: {candidate}")

    if not success2:
        logger.warning("⚠️ No pitcher fetch script found - predictions may lack pitcher data")
    else:
        # Re-run games fetch to merge newly fetched pitcher names into games file
        logger.info("\n🔁 STEP 2B: Re-fetching Games to Merge Pitchers")
        success1b = False
        for candidate in games_candidates:
            if candidate.exists():
                success1b = run_script(candidate, f"Re-Fetch Today's Games for Pitcher Merge ({candidate.name})", logger, 300)
                if success1b:
                    break
        if not success1b:
            logger.warning("⚠️ Pitchers fetched but failed to re-merge into games file")
    
    # Step 2.5: Update Core Data Files (CRITICAL - Must run before predictions)
    logger.info("\n🔄 STEP 2.5: Updating Core Data Files")
    
    # Step 2.5a: Generate Weather & Park Factors (PRIORITY - affects predictions)
    logger.info("🌤️ Generating weather and park factors...")
    weather_script = base_dir / "weather_park_integration.py"
    if weather_script.exists():
        success_weather = run_script(weather_script, "Generate Weather & Park Factors", logger, 180)
        if success_weather:
            logger.info("✅ Weather and park factors generated")
        else:
            logger.warning("⚠️ Weather generation failed - using static park factors only")
    else:
        logger.warning("⚠️ Weather integration script not found - using cached weather data")
    
    # Update pitcher stats first (affects today's games)
    logger.info("📊 Updating pitcher statistics...")
    pitcher_updater = base_dir / "fast_pitcher_updater.py"
    if pitcher_updater.exists():
        success_pitcher = run_script(pitcher_updater, "Update Pitcher Stats", logger, 180)
        if success_pitcher:
            logger.info("✅ Pitcher stats updated")
        else:
            logger.warning("⚠️ Pitcher stats update failed - using cached data")
    else:
        logger.warning("⚠️ Pitcher updater not found - using cached pitcher data")

    # NEW: Fetch Bovada pitcher props
    logger.info("🧾 Fetching Bovada pitcher prop lines...")
    bovada_script = base_dir / "fetch_bovada_pitcher_props.py"
    success_bovada = False
    if bovada_script.exists():
        success_bovada = run_script(bovada_script, "Fetch Bovada Pitcher Props", logger, 180)
    else:
        logger.warning("⚠️ Bovada pitcher props script not found")

    # NEW: Daily pitcher props model retraining BEFORE generating projections
    logger.info("🧪 STEP 2.6: Daily Pitcher Props Model Retraining")
    # 1) Build enriched projection features for today (used by historical dataset)
    proj_features_script = base_dir / "pitcher_projections.py"
    if proj_features_script.exists():
        run_script(proj_features_script, "Build Pitcher Projection Features (today)", logger, 420)
    else:
        logger.warning("⚠️ pitcher_projections.py not found - dataset may miss today's features")

    # 2) Update historical dataset from daily snapshots
    hist_dataset_script = base_dir / "historical_pitcher_prop_dataset.py"
    if hist_dataset_script.exists():
        run_script(hist_dataset_script, "Update Historical Pitcher Props Dataset", logger, 180)
    else:
        logger.warning("⚠️ historical_pitcher_prop_dataset.py not found - skipping dataset append")

    # 3) Try to ingest outcomes into dataset CSV and augment targets
    upd_outcomes_script = base_dir / "update_pitcher_prop_outcomes.py"
    if upd_outcomes_script.exists():
        run_script(upd_outcomes_script, "Update Pitcher Prop Outcomes (box scores)", logger, 300)
    else:
        logger.info("ℹ️ update_pitcher_prop_outcomes.py not found - relying on realized_results file if present")

    augment_targets_script = base_dir / "training" / "augment_with_outcomes.py"
    if augment_targets_script.exists():
        run_script(augment_targets_script, "Augment Dataset With Targets", logger, 180)
    else:
        logger.warning("⚠️ training/augment_with_outcomes.py not found - training may fallback to projections as targets")

    # 4) Train pitcher models (scikit-learn). If deps missing, script will exit gracefully.
    train_pitcher_models_script = base_dir / "training" / "train_pitcher_models.py"
    latest_models_version = None
    if train_pitcher_models_script.exists():
        ok_train = run_script(train_pitcher_models_script, "Train Pitcher Prop Models", logger, 900)
        # Promote latest trained version for runtime if available
        try:
            models_root = base_dir / 'models' / 'pitcher_props'
            if models_root.exists():
                # Find newest version dir by mtime
                subdirs = [p for p in models_root.iterdir() if p.is_dir()]
                if subdirs:
                    subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    latest_dir = subdirs[0]
                    meta = latest_dir / 'metadata.json'
                    ver = None
                    if meta.exists():
                        import json
                        with meta.open('r', encoding='utf-8') as f:
                            mdoc = json.load(f) or {}
                            ver = mdoc.get('version')
                    if not ver:
                        ver = latest_dir.name
                    promoted = models_root / 'promoted.json'
                    with promoted.open('w', encoding='utf-8') as f:
                        import json
                        json.dump({'version': ver, 'path': latest_dir.name, 'promoted_at': datetime.now().isoformat()}, f, indent=2)
                    latest_models_version = ver
                    logger.info(f"🏷️ Promoted pitcher models version: {ver}")
        except Exception as e:
            logger.warning(f"⚠️ Could not promote latest pitcher models: {e}")
    else:
        logger.info("ℹ️ training/train_pitcher_models.py not found - skipping training step")

    # 5) Now generate pitcher prop projections & recommendations (will use models if available)
    logger.info("📐 Generating pitcher prop projections & recommendations...")
    pitcher_prop_proj_script = base_dir / "generate_pitcher_prop_projections.py"
    success_pitcher_prop_recs = False
    if pitcher_prop_proj_script.exists():
        success_pitcher_prop_recs = run_script(pitcher_prop_proj_script, "Generate Pitcher Prop Projections", logger, 240)
    else:
        logger.warning("⚠️ Pitcher prop projections script not found")
    
    # Retry props fetch/generate if empty (Bovada can lag early morning)
    try:
        import json as _json, time as _time
        props_dir = data_dir / 'daily_bovada'
        props_dir.mkdir(parents=True, exist_ok=True)
        props_path = props_dir / f"bovada_pitcher_props_{today_underscore}.json"
        last_known_path = props_dir / f"pitcher_last_known_lines_{today_underscore}.json"

        def _props_empty(p: Path) -> bool:
            try:
                if not p.exists() or p.stat().st_size == 0:
                    return True
                with p.open('r', encoding='utf-8') as f:
                    j = _json.load(f)
                m = j.get('pitcher_props') if isinstance(j, dict) else None
                return not (isinstance(m, dict) and len(m) > 0)
            except Exception:
                return True

        if _props_empty(props_path):
            logger.info("⏳ Props file empty after initial pass; retrying fetch/generate up to 2 more times...")
            for attempt in (2, 3):
                _time.sleep(45)
                if bovada_script.exists():
                    run_script(bovada_script, f"[Retry {attempt}] Fetch Bovada Pitcher Props", logger, 180)
                if pitcher_prop_proj_script.exists():
                    run_script(pitcher_prop_proj_script, f"[Retry {attempt}] Generate Pitcher Prop Projections", logger, 180)
                if not _props_empty(props_path):
                    logger.info(f"✅ Props populated on retry {attempt}")
                    break
            else:
                logger.warning("⚠️ Props still empty after retries; frontend will rely on manual/continuous refresh.")
        # Seed last-known snapshot if present props but missing/empty last-known
        def _last_known_empty(p: Path) -> bool:
            try:
                if not p.exists() or p.stat().st_size == 0:
                    return True
                with p.open('r', encoding='utf-8') as f:
                    j = _json.load(f)
                m = j.get('pitchers') if isinstance(j, dict) else None
                return not (isinstance(m, dict) and len(m) > 0)
            except Exception:
                return True
        try:
            if not _props_empty(props_path) and _last_known_empty(last_known_path):
                with props_path.open('r', encoding='utf-8') as f:
                    pdoc = _json.load(f) or {}
                pitchers = pdoc.get('pitcher_props') or {}
                out = {'date': today, 'updated_at': datetime.now().isoformat(), 'pitchers': {}}
                for raw_key, mkts in (pitchers.items() if isinstance(pitchers, dict) else []):
                    try:
                        name_only = str(raw_key).split('(')[0].strip()
                        nk = name_only.lower()
                        mkout = {}
                        if isinstance(mkts, dict):
                            for mk, info in mkts.items():
                                if isinstance(info, dict) and (info.get('line') is not None):
                                    mkout[mk] = {
                                        'line': info.get('line'),
                                        'over_odds': info.get('over_odds'),
                                        'under_odds': info.get('under_odds')
                                    }
                        if mkout:
                            out['pitchers'][nk] = mkout
                    except Exception:
                        continue
                if out['pitchers']:
                    tmp = last_known_path.with_suffix('.json.tmp')
                    with tmp.open('w', encoding='utf-8') as f:
                        _json.dump(out, f, ensure_ascii=False, indent=2)
                    tmp.replace(last_known_path)
                    logger.info(f"🧭 Seeded last-known snapshot: {last_known_path.name} with {len(out['pitchers'])} pitchers")
        except Exception as se:
            logger.debug(f"Last-known seeding skipped: {se}")
    except Exception as e:
        logger.debug(f"Props retry guard failed: {e}")
    
    # Update team strengths (affects predictions)
    logger.info("🏟️ Updating team strength ratings...")
    team_updater = base_dir / "weekly_team_updater.py"
    if team_updater.exists():
        success_teams = run_script(team_updater, "Update Team Strengths", logger, 120)
        if success_teams:
            logger.info("✅ Team strengths updated")
        else:
            logger.warning("⚠️ Team strength update failed - using cached data")
    else:
        logger.warning("⚠️ Team updater not found - using cached team data")
    
    # Update comprehensive daily data (bullpen, weather, etc.)
    logger.info("🌐 Updating comprehensive daily data...")
    daily_updater = base_dir / "daily_data_updater.py"
    if daily_updater.exists():
        success_daily = run_script(daily_updater, "Update Daily Data", logger, 300)  # Increased timeout to 300s
        if success_daily:
            logger.info("✅ Daily data updated (bullpen, weather factors)")
        else:
            logger.warning("⚠️ Daily data update failed - using cached data")
    else:
        logger.warning("⚠️ Daily data updater not found - using cached daily data")
    
    # Step 3: Fetch Real Betting Lines
    logger.info("\n🎯 STEP 3: Fetching Real Betting Lines (DraftKings preferred)")
    logger.info("💰 Connecting to OddsAPI for current betting odds...")
    step_start = datetime.now()
    
    lines_candidates = [
        base_dir / "fetch_betting_lines_simple.py",  # DK-focused builder
        base_dir / "fetch_betting_lines_real.py"
    ]

    success3 = False
    for candidate in lines_candidates:
        if candidate.exists():
            # longer timeout to allow API rate limits
            logger.info(f"📡 Running {candidate.name} (this may take 2-3 minutes)...")
            success3 = run_script(candidate, f"Fetch Betting Lines ({candidate.name})", logger, 900)
            if success3:
                break
        else:
            logger.debug(f"Lines fetch candidate not found: {candidate}")

    step_duration = (datetime.now() - step_start).total_seconds()
    
    # Fallback: try importing and calling directly
    if not success3:
        logger.info("🔄 Trying fallback import method...")
        try:
            import importlib
            for modname in ("fetch_betting_lines_simple", "fetch_betting_lines_real"):
                try:
                    mod = importlib.import_module(modname)
                    if hasattr(mod, 'main'):
                        logger.info(f"🔁 Running {modname}.main() as fallback")
                        ok = bool(mod.main())
                        success3 = success3 or ok
                        if success3:
                            break
                except Exception as ie:
                    logger.debug(f"Fallback import failed for {modname}: {ie}")
            if not success3:
                raise RuntimeError("No betting lines module succeeded")
        except Exception as e:
            logger.warning(f"⚠️ No real betting lines available after {step_duration:.1f}s - continuing without them")
            logger.info("📋 To get real betting lines:")
            logger.info("   1. Get an OddsAPI key from https://the-odds-api.com/")
            logger.info("   2. Add it to data/closing_lines_config.json")
            logger.info("   3. Re-run the automation")
    
    if success3:
        logger.info(f"✅ Betting lines fetched successfully ({step_duration:.1f}s)")

    # Step 3.5: Daily games model retuning before generating predictions
    logger.info("\n🧪 STEP 3.5: Daily Games Model Retuning")
    retuner_script = base_dir / "comprehensive_model_retuner.py"
    if retuner_script.exists():
        # Run a shorter window retune daily (e.g., last 7-10 days)
        retune_ok = run_script(retuner_script, "Run Comprehensive Model Retuner (daily)", logger, 900)
        # Sync the optimized config to engine's default read path if present
        try:
            src_cfg = base_dir / 'data' / 'comprehensive_optimized_config.json'
            dst_cfg = base_dir / 'data' / 'optimized_config.json'
            if src_cfg.exists():
                shutil.copy2(src_cfg, dst_cfg)
                logger.info("🔄 Synced comprehensive_optimized_config.json -> optimized_config.json for engine usage")
        except Exception as e:
            logger.warning(f"⚠️ Could not sync optimized config for engine: {e}")
    else:
        logger.info("ℹ️ comprehensive_model_retuner.py not found - skipping daily retune")
    
    # Step 4: Generate Today's Predictions
    logger.info("\n🎯 STEP 4: Generating Today's Predictions")
    prediction_candidates = [
        base_dir / "daily_ultrafastengine_predictions.py"
    ]

    success4 = False
    for candidate in prediction_candidates:
        if candidate.exists():
            success4 = run_script(candidate, f"Generate Today's Predictions ({candidate.name})", logger, 900)
            if success4:
                break
        else:
            logger.debug(f"Prediction candidate not found: {candidate}")
            
    if not success4:
        logger.warning("⚠️ No prediction script found - betting engine will use existing cache if available")
    
    # Step 5: Generate Betting Recommendations
    logger.info("\n🎯 STEP 5: Generating Betting Recommendations")
    betting_candidates = [
        base_dir / "unified_betting_engine.py",
        base_dir / "betting_recommendations_engine.py",
        base_dir / "app_betting_integration.py"
    ]

    success5 = False
    for candidate in betting_candidates:
        if candidate.exists():
            success5 = run_script(candidate, f"Generate Betting Recommendations ({candidate.name})", logger, 300)
            if success5:
                break
        else:
            logger.debug(f"Betting candidate not found: {candidate}")

    # Step 6: Run Comprehensive Analysis
    logger.info("\n📊 STEP 6: Running Comprehensive Analysis")
    analysis_script = base_dir / "comprehensive_mlb_analysis_system.py"
    success6 = False
    
    if analysis_script.exists():
        success6 = run_script(analysis_script, "Run Comprehensive Analysis", logger, 180)
    else:
        logger.warning("❌ Comprehensive analysis script not found")
    
    # Step 7: Update Frontend Data
    logger.info("\n🔄 STEP 7: Updating Frontend Data")
    frontend_script = base_dir / "update_frontend_analysis.py"
    success7 = False
    
    if frontend_script.exists():
        success7 = run_script(frontend_script, "Update Frontend Analysis", logger, 60)
    else:
        logger.warning("❌ Frontend update script not found")

    # Fallback: import unified_betting_engine and call main() or generate_recommendations()
    if not success5:
        try:
            import importlib
            ube = importlib.import_module('unified_betting_engine')
            if hasattr(ube, 'main'):
                logger.info("🔁 Running unified_betting_engine.main() as fallback")
                try:
                    ube.main()
                    success5 = True
                except Exception as e:
                    logger.error(f"Unified engine main() failed: {e}")
            else:
                # Try programmatic use
                if hasattr(ube, 'UnifiedBettingEngine'):
                    logger.info("🔁 Running UnifiedBettingEngine.generate_recommendations() as fallback")
                    try:
                        engine = ube.UnifiedBettingEngine()
                        recs = engine.generate_recommendations()
                        if recs and engine.save_recommendations(recs):
                            success5 = True
                    except Exception as e:
                        logger.error(f"Unified engine programmatic run failed: {e}")
        except Exception as e:
            logger.debug(f"Fallback betting recommendations import failed: {e}")
    
    # Step 6: Copy files to correct locations
    logger.info("\n🎯 STEP 6: Copying Files to MLB-Betting Directory")
    
    files_to_copy = [
        (data_dir / "unified_predictions_cache.json", mlb_betting_data_dir / "unified_predictions_cache.json"),
        (data_dir / f"betting_recommendations_{today_underscore}.json", mlb_betting_data_dir / f"betting_recommendations_{today_underscore}.json"),
        (data_dir / f"real_betting_lines_{today_underscore}.json", mlb_betting_data_dir / f"real_betting_lines_{today_underscore}.json"),
        (data_dir / f"games_{today}.json", mlb_betting_data_dir / f"games_{today}.json"),
    ]
    
    copy_success = True
    for source, target in files_to_copy:
        if not copy_file_safe(source, target, logger):
            copy_success = False
    
    # Step 7: Verify data integrity
    logger.info("\n🎯 STEP 7: Verifying Data Integrity")
    
    # Check unified cache
    unified_cache_path = mlb_betting_data_dir / "unified_predictions_cache.json"
    betting_recs_path = mlb_betting_data_dir / f"betting_recommendations_{today_underscore}.json"
    betting_lines_path = mlb_betting_data_dir / f"real_betting_lines_{today_underscore}.json"
    games_path = mlb_betting_data_dir / f"games_{today}.json"
    
    cache_ok = unified_cache_path.exists()
    betting_ok = betting_recs_path.exists()
    lines_ok = betting_lines_path.exists()
    games_ok = games_path.exists()
    
    def ensure_today_in_unified_cache(unified_cache_path: Path, games_path: Path, betting_recs_path: Path) -> bool:
        """If today's predictions are missing in unified cache, synthesize from games + betting_recommendations.
        Returns True if unified cache was updated (or already had today), False on hard failure.
        """
        try:
            import json
            if not games_path.exists():
                logger.warning(f"⚠️ Cannot build unified cache: games file missing: {games_path}")
                return False
            if not betting_recs_path.exists():
                logger.warning(f"⚠️ Cannot build unified cache fully: betting recommendations missing: {betting_recs_path}")
                # We'll still try to build a skeletal entry from games only
            # Load current unified cache or start a fresh structure
            cache_data = {}
            if unified_cache_path.exists():
                try:
                    with open(unified_cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                except Exception:
                    cache_data = {}
            if 'predictions_by_date' not in cache_data:
                cache_data['predictions_by_date'] = {}

            # Load files
            with open(games_path, 'r', encoding='utf-8') as f:
                games_list = json.load(f) or []
            betting_doc = {}
            if betting_recs_path.exists():
                try:
                    with open(betting_recs_path, 'r', encoding='utf-8') as f:
                        betting_doc = json.load(f) or {}
                except Exception:
                    betting_doc = {}
            rec_games = betting_doc.get('games', {}) if isinstance(betting_doc, dict) else {}

            def match_rec(away: str, home: str):
                # Robust match by team names across all rec entries
                if not isinstance(rec_games, dict):
                    return {}
                for _, v in rec_games.items():
                    if not isinstance(v, dict):
                        continue
                    if v.get('away_team') == away and v.get('home_team') == home:
                        return v
                return {}

            def keyify(away: str, home: str) -> str:
                return f"{away}_vs_{home}".replace(' ', '_')

            unified_games = {}
            for g in (games_list or []):
                away = g.get('away_team') or ''
                home = g.get('home_team') or ''
                if not away or not home:
                    continue
                rec = match_rec(away, home)
                preds = rec.get('predictions', {}) if isinstance(rec, dict) else {}
                unified_games[keyify(away, home)] = {
                    'away_team': away,
                    'home_team': home,
                    'game_date': today,
                    'game_time': g.get('game_time', ''),
                    'away_pitcher': g.get('away_pitcher', 'TBD'),
                    'home_pitcher': g.get('home_pitcher', 'TBD'),
                    'predictions': preds,
                    'betting_lines': rec.get('betting_lines', {}),
                    'recommendations': rec.get('recommendations', []) or rec.get('value_bets', []),
                    'pitcher_info': rec.get('pitcher_info', {}),
                    'source': 'daily_files'
                }

            cache_data['predictions_by_date'][today] = {
                'games': unified_games,
                'timestamp': datetime.now().isoformat(),
                'total_games': len(unified_games),
                'source': 'daily_files',
                'games_file': str(games_path),
                'betting_file': str(betting_recs_path) if betting_recs_path.exists() else None
            }

            unified_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(unified_cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"✅ Injected today's predictions into unified cache: {unified_cache_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to ensure today's unified cache: {e}")
            return False

    if cache_ok:
        try:
            import json
            with open(unified_cache_path, 'r') as f:
                cache_data = json.load(f)
                dates = list(cache_data.get('predictions_by_date', {}).keys())
                has_today = today in dates
                games_count = len(cache_data.get('predictions_by_date', {}).get(today, {}).get('games', {}))
                
                logger.info(f"✅ Unified cache loaded: {len(dates)} dates, today included: {has_today}, games today: {games_count}")
                if not has_today or games_count == 0:
                    logger.warning(f"⚠️ Cache missing today's data: has_today={has_today}, games_count={games_count}")
                    # Attempt to build today's entry from games + betting recommendations
                    built = ensure_today_in_unified_cache(unified_cache_path, games_path, betting_recs_path)
                    if built:
                        # Re-check counts after injection
                        try:
                            with open(unified_cache_path, 'r', encoding='utf-8') as rf:
                                rc = json.load(rf)
                                games_count2 = len(rc.get('predictions_by_date', {}).get(today, {}).get('games', {}))
                                logger.info(f"🔁 Unified cache rebuilt for today: games now: {games_count2}")
                        except Exception:
                            pass
                        cache_ok = True
                    else:
                        # Allow system to continue - engine can still work, but note degraded state
                        cache_ok = True
                else:
                    cache_ok = True
        except Exception as e:
            logger.error(f"❌ Error reading unified cache: {e}")
            cache_ok = False
    else:
        logger.error("❌ Unified cache file not found")
    
    if betting_ok:
        try:
            import json
            with open(betting_recs_path, 'r') as f:
                betting_data = json.load(f)
                games_with_betting = len(betting_data.get('games', {}))
                logger.info(f"✅ Betting recommendations loaded: {games_with_betting} games")
        except Exception as e:
            logger.error(f"❌ Error reading betting recommendations: {e}")
            betting_ok = False
    else:
        logger.warning("⚠️ Betting recommendations file not found")
        
    if lines_ok:
        try:
            import json
            with open(betting_lines_path, 'r') as f:
                lines_data = json.load(f)
                lines_count = len(lines_data.get('lines', {}))
                logger.info(f"✅ Betting lines loaded: {lines_count} games")
        except Exception as e:
            logger.error(f"❌ Error reading betting lines: {e}")
            lines_ok = False
    else:
        logger.warning("⚠️ Betting lines file not found (continuing without real odds)")
        
    if games_ok:
        try:
            import json
            with open(games_path, 'r') as f:
                games_data = json.load(f)
                games_count = len(games_data) if isinstance(games_data, list) else len(games_data.get('games', {}))
                logger.info(f"✅ Games data loaded: {games_count} games")
        except Exception as e:
            logger.error(f"❌ Error reading games data: {e}")
            games_ok = False
    else:
        logger.warning("⚠️ Games data file not found")
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 AUTOMATION SUMMARY")
    logger.info("=" * 80)
    
    steps = [
        ("Fetch Today's Games", success1),
        ("Fetch Probable Pitchers", success2),
        ("Fetch Bovada Pitcher Props", locals().get('success_bovada', False)),
        ("Generate Pitcher Prop Projections", locals().get('success_pitcher_prop_recs', False)),
        ("Fetch Betting Lines", success3),
        ("Generate Predictions", success4),
        ("Generate Betting Recommendations", success5),
        ("File Copying", copy_success),
        ("Unified Cache Verification", cache_ok),
        ("Betting Recommendations Verification", betting_ok),
        ("Betting Lines Verification", lines_ok),
        ("Games Data Verification", games_ok)
    ]
    
    all_success = True
    critical_success = True  # Track critical components
    # On no-games day, predictions aren't required; focus on files being present and cache integrity
    if os.environ.get('NO_GAMES_MODE', '').lower() in ('1', 'true', 'yes'):
        critical_steps = ["Unified Cache Verification", "Games Data Verification", "File Copying"]
    else:
        critical_steps = ["Fetch Today's Games", "Generate Predictions", "Unified Cache Verification", "Games Data Verification"]
    
    for step_name, success in steps:
        status = "✅ PASS" if success else "❌ FAIL"
        # If it's a no-games day, mark heavy steps as skipped without counting as a failure
        if os.environ.get('NO_GAMES_MODE', '').lower() in ('1', 'true', 'yes'):
            no_games_skippable = {
                "Fetch Probable Pitchers",
                "Fetch Bovada Pitcher Props",
                "Generate Pitcher Prop Projections",
                "Fetch Betting Lines",
                "Generate Predictions",
                "Generate Betting Recommendations",
            }
            if step_name in no_games_skippable and not success:
                status = "⏭️ SKIP (no games)"
                # Do not penalize overall success
                logger.info(f"{step_name}: {status}")
                continue
        # Mark non-critical betting lines as optional on normal days
        if step_name in ["Fetch Betting Lines", "Betting Lines Verification"] and not success:
            status = "⚠️ SKIP (no real odds available)"
        logger.info(f"{step_name}: {status}")
        
        if not success:
            all_success = False
            # Only mark as critical failure if it's a critical step
            if step_name in critical_steps:
                critical_success = False
    
    # Final step: write Kelly 'Best of Best' entries for yesterday so the tab persists daily
    try:
        writer = base_dir / 'write_kelly_best_of_best.py'
        if writer.exists():
            logger.info("\n🎯 FINAL STEP: Writing Kelly 'Best of Best' entries for yesterday")
            run_script(writer, "Write Kelly Best of Best (yesterday)", logger, 180)
            # Also write today's Kelly after recs so frontend shows correct totals immediately
            try:
                today_arg = f"--date={today}"
                logger.info("🗓️ Writing Kelly 'Best of Best' entries for today as well")
                subprocess.run([sys.executable, str(writer), today_arg], cwd=str(base_dir), check=False)
            except Exception as e:
                logger.debug(f"Could not write today's Kelly file: {e}")
        else:
            logger.warning("⚠️ Kelly writer script not found; skipping persistent Kelly output")
    except Exception as e:
        logger.warning(f"⚠️ Kelly writer step failed: {e}")

    # Optional: If Sunday, run weekly retune after core pipeline
    try:
        from datetime import date
        if datetime.now().weekday() == 6:  # Sunday
            logger.info("\n🔁 SUNDAY DETECTED: Triggering weekly_retune.py for rolling optimization")
            retune_script = Path(__file__).parent / 'weekly_retune.py'
            if retune_script.exists():
                run_script(retune_script, 'Weekly Retune (auto Sunday)', logger, 600)
            else:
                logger.warning("⚠️ weekly_retune.py not found; skipping auto weekly retune")
    except Exception as e:
        logger.warning(f"⚠️ Weekly retune auto-trigger failed: {e}")

    # Auto Git push of any updated data/code (optional, enabled by default)
    def auto_git_push(repo_dir: Path, logger, today_str: str):
        try:
            # Allow disabling via env var
            if os.environ.get('AUTO_GIT_PUSH_DISABLED', '').lower() in ('1', 'true', 'yes'):
                logger.info("🛑 Auto git push disabled via AUTO_GIT_PUSH_DISABLED env var")
                return

            def git(args, check=False):
                res = subprocess.run(['git'] + list(args), cwd=str(repo_dir), capture_output=True, text=True)
                if check and res.returncode != 0:
                    raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr or res.stdout}")
                return res

            # Verify we're in a git repo
            res = git(['rev-parse', '--is-inside-work-tree'])
            if res.returncode != 0 or 'true' not in (res.stdout or '').lower():
                logger.info("ℹ️ Not a git repository; skipping auto push")
                return

            # Detect changes
            status = git(['status', '--porcelain'])
            changed = []
            if status.stdout:
                changed = [line.strip() for line in status.stdout.splitlines() if line.strip()]
            if not changed:
                logger.info("🧹 No changes to commit; skipping auto push")
                return

            # Stage all changes
            git(['add', '-A'], check=True)

            # Commit
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_msg = (
                f"Automation: update daily data for {today_str} at {timestamp}\n\n" \
                f"Files: {min(len(changed), 20)} changed (showing up to 20)\n" \
                + '\n'.join(changed[:20])
            )
            commit = git(['commit', '-m', commit_msg])
            if commit.returncode != 0:
                # Possibly nothing to commit (race), recheck and bail
                logger.info(f"ℹ️ Commit skipped: {commit.stderr.strip() or commit.stdout.strip()}")
                return

            # Push (non-fatal if it fails)
            push = git(['push'])
            if push.returncode == 0:
                logger.info("🚀 Auto-pushed changes to remote")
            else:
                logger.warning(f"⚠️ Auto push failed: {push.stderr.strip() or push.stdout.strip()}")
        except Exception as e:
            logger.warning(f"⚠️ Auto git push encountered an issue: {e}")

    # Run auto git push regardless of success outcome if there are changes
    try:
        auto_git_push(base_dir, logger, today)
    except Exception as e:
        logger.debug(f"Auto git push wrapper failed: {e}")

    if all_success:
        logger.info("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        logger.info(f"🎯 Ready for MLB betting analysis on {today}")
        return True
    elif critical_success and (success4 or cache_ok):  # Allow partial success if predictions/cache are OK
        logger.warning("\n⚠️ PARTIAL SUCCESS - Core functionality available")
        logger.info(f"🎯 Basic MLB analysis available on {today}")
        return True
    else:
        logger.error("\n❌ CRITICAL STEPS FAILED - System not ready")
        logger.error("🚨 Manual intervention required to fix data pipeline")
        return False

if __name__ == "__main__":
    success = complete_daily_automation()
    sys.exit(0 if success else 1)
