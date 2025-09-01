import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from historical_analysis_endpoint import analyzer


def count_ready(d: str):
    games = analyzer.load_predictions_for_date(d)
    ready = 0
    for k, g in (games or {}).items():
        pv = analyzer.extract_prediction_values(g)
        if (
            pv['away_win_probability'] is not None
            and pv['home_win_probability'] is not None
            and pv['predicted_away_score'] is not None
            and pv['predicted_home_score'] is not None
        ):
            ready += 1
    print(f"{d} -> total_games={len(games or {})}, ready_for_predictability={ready}")


def show_matched(d: str):
    analysis = analyzer.perform_complete_analysis(d)
    pred = analysis.get('predictability', {})
    print(
        f"{d} -> matched_games={pred.get('matched_games', 0)}, winner_acc={pred.get('winner_accuracy', 0.0)}"
    )


if __name__ == "__main__":
    for d in ["2025-08-22", "2025-08-23"]:
        count_ready(d)
        show_matched(d)
