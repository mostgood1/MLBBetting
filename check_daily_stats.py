import json
import os
from team_name_normalizer import normalize_team_name

def calculate_american_odds_payout(odds, bet_amount=100):
    """Calculate payout for American odds"""
    # Convert odds to int if it's a string
    if isinstance(odds, str):
        try:
            odds = int(odds)
        except ValueError:
            odds = -110  # Default odds
    
    if odds > 0:
        # Positive odds: profit = (odds/100) * bet_amount
        profit = (odds / 100) * bet_amount
    else:
        # Negative odds: profit = (100/abs(odds)) * bet_amount
        profit = (100 / abs(odds)) * bet_amount
    
    return profit

def analyze_single_date(date):
    """Analyze betting performance for a single date"""
    date_formatted = date.replace('-', '_')
    
    betting_file = f'data/betting_recommendations_{date_formatted}.json'
    final_scores_file = f'data/final_scores_{date_formatted}.json'
    
    if not os.path.exists(betting_file) or not os.path.exists(final_scores_file):
        return None
    
    # Load data
    with open(betting_file, 'r') as f:
        betting_data = json.load(f)
    
    with open(final_scores_file, 'r') as f:
        final_scores_data = json.load(f)
    
    # Create final scores lookup with normalized keys
    final_scores = {}
    for game in final_scores_data:
        away_team = normalize_team_name(game.get('away_team', ''))
        home_team = normalize_team_name(game.get('home_team', ''))
        normalized_key = f"{away_team}_vs_{home_team}"
        
        # Calculate total_runs if not present
        total_runs = game.get('total_runs')
        if total_runs is None:
            away_score = game.get('away_score', 0) or 0
            home_score = game.get('home_score', 0) or 0
            total_runs = away_score + home_score
        
        final_scores[normalized_key] = {
            'total_runs': total_runs,
            'away_score': game.get('away_score', 0) or 0,
            'home_score': game.get('home_score', 0) or 0,
            'winner': game.get('winner', '')
        }
    
    # Analyze betting recommendations
    total_bets = 0
    correct_bets = 0
    total_wagered = 0
    total_winnings = 0
    bet_details = []
    
    games = betting_data.get('games', {})
    
    for game_key, game_data in games.items():
        # Normalize the game key for matching
        parts = game_key.split('_vs_')
        if len(parts) == 2:
            away_norm = normalize_team_name(parts[0])
            home_norm = normalize_team_name(parts[1])
            normalized_key = f"{away_norm}_vs_{home_norm}"
        else:
            normalized_key = game_key
        
        if normalized_key not in final_scores:
            print(f"  No final score found for: {normalized_key}")
            continue
        
        final_score = final_scores[normalized_key]
        
        # Check both bet formats
        all_bets = []
        
        # Value bets format
        value_bets = game_data.get('value_bets', [])
        if isinstance(value_bets, list):
            for bet in value_bets:
                all_bets.append(('value_bet', bet))
        
        # Recommendations format
        recommendations = game_data.get('recommendations', [])
        if isinstance(recommendations, list):
            for bet in recommendations:
                # Skip "No Strong Value" recommendations
                if bet.get('bet') == 'No Strong Value' or bet.get('recommendation') == 'No clear value identified':
                    continue
                all_bets.append(('recommendation', bet))
        
        # Evaluate each bet
        for bet_type, bet in all_bets:
            total_bets += 1
            bet_amount = 100  # Standard bet size
            total_wagered += bet_amount
            
            # Determine bet details based on format
            if bet_type == 'value_bet':
                recommendation = bet.get('recommendation', '').lower()
                betting_line = bet.get('betting_line', 0)
                odds = bet.get('american_odds', -110)
            else:  # recommendation format
                side = bet.get('side', '').lower()
                betting_line = bet.get('line', 0)
                odds = bet.get('odds', -110)
                recommendation = side  # Use side as recommendation for this format
            
            # Evaluate over/under bets
            if 'over' in recommendation or 'under' in recommendation:
                actual_total = final_score['total_runs']
                
                if 'over' in recommendation:
                    bet_won = actual_total > betting_line
                    bet_description = f"Over {betting_line}"
                else:
                    bet_won = actual_total < betting_line
                    bet_description = f"Under {betting_line}"
                
                if bet_won:
                    correct_bets += 1
                    winnings = bet_amount + calculate_american_odds_payout(odds, bet_amount)
                    total_winnings += winnings
                    result = "WON"
                else:
                    result = "LOST"
                
                bet_details.append({
                    'game': normalized_key.replace('_', ' '),
                    'bet': bet_description,
                    'actual': actual_total,
                    'odds': odds,
                    'result': result,
                    'type': bet_type
                })
    
    if total_bets == 0:
        return None
    
    # Calculate stats
    accuracy = (correct_bets / total_bets) * 100
    net_profit = total_winnings - total_wagered
    roi = (net_profit / total_wagered) * 100
    
    return {
        'date': date,
        'total_bets': total_bets,
        'correct_bets': correct_bets,
        'accuracy': accuracy,
        'total_wagered': total_wagered,
        'total_winnings': total_winnings,
        'net_profit': net_profit,
        'roi': roi,
        'bet_details': bet_details
    }

# Test each date
dates = ['2025-08-15', '2025-08-16', '2025-08-17', '2025-08-18', '2025-08-19', 
         '2025-08-20', '2025-08-21', '2025-08-22', '2025-08-23', '2025-08-24', 
         '2025-08-25', '2025-08-26']

print("DAILY BETTING ANALYSIS:")
print("=" * 80)

overall_stats = {
    'total_bets': 0,
    'correct_bets': 0,
    'total_wagered': 0,
    'total_winnings': 0
}

for date in dates:
    result = analyze_single_date(date)
    if result:
        print(f"\n{date}:")
        print(f"  Bets: {result['total_bets']}")
        print(f"  Correct: {result['correct_bets']}")
        print(f"  Accuracy: {result['accuracy']:.1f}%")
        print(f"  ROI: {result['roi']:.1f}%")
        print(f"  Net Profit: ${result['net_profit']:.2f}")
        
        # Show first few bet details for verification
        if result['bet_details']:
            print("  Sample bets:")
            for bet in result['bet_details'][:3]:
                print(f"    {bet['game']}: {bet['bet']} (actual: {bet['actual']}) - {bet['result']} [{bet['type']}]")
        
        # Add to overall stats
        overall_stats['total_bets'] += result['total_bets']
        overall_stats['correct_bets'] += result['correct_bets']
        overall_stats['total_wagered'] += result['total_wagered']
        overall_stats['total_winnings'] += result['total_winnings']
    else:
        print(f"\n{date}: No data available")

# Calculate overall stats
if overall_stats['total_bets'] > 0:
    overall_accuracy = (overall_stats['correct_bets'] / overall_stats['total_bets']) * 100
    overall_net_profit = overall_stats['total_winnings'] - overall_stats['total_wagered']
    overall_roi = (overall_net_profit / overall_stats['total_wagered']) * 100
    
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY:")
    print(f"Total Bets: {overall_stats['total_bets']}")
    print(f"Correct Bets: {overall_stats['correct_bets']}")
    print(f"Overall Accuracy: {overall_accuracy:.1f}%")
    print(f"Total Wagered: ${overall_stats['total_wagered']:.2f}")
    print(f"Total Winnings: ${overall_stats['total_winnings']:.2f}")
    print(f"Net Profit: ${overall_net_profit:.2f}")
    print(f"Overall ROI: {overall_roi:.1f}%")
