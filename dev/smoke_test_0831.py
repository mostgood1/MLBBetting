from historical_analysis_endpoint import analyzer

report = analyzer.perform_complete_analysis('2025-08-31')
print('date:', report.get('date'))
print('final_scores_missing:', report.get('final_scores_missing'))
pred = report.get('predictability', {})
print('predictability:', {
    'matched_games': pred.get('matched_games'),
    'winner_accuracy': pred.get('winner_accuracy'),
    'avg_away_score_error': pred.get('avg_away_score_error'),
    'avg_home_score_error': pred.get('avg_home_score_error'),
    'percent_total_within_1': pred.get('percent_total_within_1'),
    'percent_total_within_2': pred.get('percent_total_within_2'),
})
print('data_summary:', report.get('data_summary'))
