from engines.ultra_fast_engine import UltraFastSimEngine

# Simple local check that two DH games with flipped starters produce different projections

def run_check():
    engine = UltraFastSimEngine()
    date_str = None  # use today's date if available; engine doesn't require it for pitcher overrides
    away_team = "Atlanta Braves"
    home_team = "Washington Nationals"

    # Game 1 starters
    g1_away_p = "Chris Sale"
    g1_home_p = "MacKenzie Gore"

    # Game 2 starters (example flipped/different)
    g2_away_p = "Jose Suarez"  # avoid accent issues in some datasets
    g2_home_p = "Jake Irvin"

    for label, ap, hp in [("G1", g1_away_p, g1_home_p), ("G2", g2_away_p, g2_home_p)]:
        results, info = engine.simulate_game_vectorized(away_team, home_team, sim_count=5000, game_date=date_str, away_pitcher=ap, home_pitcher=hp)
        total = len(results)
        home_wins = sum(1 for r in results if r.home_wins)
        avg_home = sum(r.home_score for r in results) / total
        avg_away = sum(r.away_score for r in results) / total
        home_wp = home_wins / total
        print(f"{label}: {away_team} @ {home_team} | {ap} vs {hp} -> Home WP: {home_wp:.4f}, Scores A/H: {avg_away:.2f}/{avg_home:.2f}")
        print(f"Pitcher factors (away vs home): {info.get('away_pitcher_factor'):.3f} vs {info.get('home_pitcher_factor'):.3f}")

if __name__ == "__main__":
    run_check()
