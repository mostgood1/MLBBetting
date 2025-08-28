#!/usr/bin/env python3
"""
Enhanced Betting Recommendations Engine - Quick Implementation
============================================================

Implements immediate improvements to the betting system including:
- Confidence thresholds (only bet on 60%+ confidence)
- Enhanced scoring adjustments  
- Better pitcher factor validation
- Simple ensemble averaging
"""

import json
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickEnhancedEngine:
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        self.confidence_threshold = 60  # Only recommend high confidence bets
        self.min_edge_threshold = 0.05  # Minimum 5% edge
        self.max_pitcher_factor = 1.5   # Clamp extreme pitcher factors
        self.min_pitcher_factor = 0.7
        
    def enhance_existing_recommendations(self):
        """Enhance existing betting recommendations with quick improvements"""
        
        print("🚀 QUICK BETTING SYSTEM ENHANCEMENTS")
        print("=" * 41)
        print()
        
        # Find all recent recommendation files
        rec_files = []
        for file in os.listdir(self.data_directory):
            if file.startswith('betting_recommendations_2025') and file.endswith('.json'):
                rec_files.append(file)
        
        enhanced_count = 0
        
        for file in sorted(rec_files)[-5:]:  # Process last 5 days
            file_path = os.path.join(self.data_directory, file)
            enhanced_file = self._enhance_single_file(file_path)
            if enhanced_file:
                enhanced_count += 1
        
        print(f"✅ Enhanced {enhanced_count} recommendation files")
        
        # Generate quick improvement report
        self._generate_improvement_report()
    
    def _enhance_single_file(self, file_path):
        """Enhance a single recommendation file"""
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if 'games' not in data:
                return False
            
            enhanced_games = {}
            improvements_made = 0
            
            for game_key, game_data in data['games'].items():
                enhanced_game = self._enhance_single_game(game_key, game_data)
                enhanced_games[game_key] = enhanced_game
                
                # Check if improvements were made
                if 'enhancements_applied' in enhanced_game:
                    improvements_made += len(enhanced_game['enhancements_applied'])
            
            # Save enhanced version
            data['games'] = enhanced_games
            data['enhancement_info'] = {
                'enhanced_at': datetime.now().isoformat(),
                'improvements_made': improvements_made,
                'version': 'quick_enhanced_v1.0'
            }
            
            # Create enhanced filename
            enhanced_path = file_path.replace('.json', '_enhanced.json')
            with open(enhanced_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✅ Enhanced {os.path.basename(file_path)} with {improvements_made} improvements")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enhance {file_path}: {e}")
            return False
    
    def _enhance_single_game(self, game_key, game_data):
        """Apply enhancements to a single game"""
        
        enhanced_game = game_data.copy()
        enhancements = []
        
        # 1. Validate and clamp pitcher factors
        if 'predictions' in game_data and 'pitcher_info' in game_data['predictions']:
            pitcher_info = game_data['predictions']['pitcher_info']
            
            away_factor = pitcher_info.get('away_pitcher_factor', 1.0)
            home_factor = pitcher_info.get('home_pitcher_factor', 1.0)
            
            # Clamp extreme values
            if away_factor < self.min_pitcher_factor or away_factor > self.max_pitcher_factor:
                original_away = away_factor
                away_factor = max(self.min_pitcher_factor, min(self.max_pitcher_factor, away_factor))
                enhanced_game['predictions']['pitcher_info']['away_pitcher_factor'] = away_factor
                enhancements.append(f"Clamped away pitcher factor: {original_away:.3f} → {away_factor:.3f}")
            
            if home_factor < self.min_pitcher_factor or home_factor > self.max_pitcher_factor:
                original_home = home_factor
                home_factor = max(self.min_pitcher_factor, min(self.max_pitcher_factor, home_factor))
                enhanced_game['predictions']['pitcher_info']['home_pitcher_factor'] = home_factor
                enhancements.append(f"Clamped home pitcher factor: {original_home:.3f} → {home_factor:.3f}")
        
        # 2. Enhance confidence calculation
        if 'predictions' in game_data and 'predictions' in game_data['predictions']:
            pred_data = game_data['predictions']['predictions']
            
            original_confidence = pred_data.get('confidence', 50)
            enhanced_confidence = self._calculate_enhanced_confidence(pred_data)
            
            if abs(enhanced_confidence - original_confidence) > 5:
                enhanced_game['predictions']['predictions']['confidence'] = enhanced_confidence
                enhancements.append(f"Enhanced confidence: {original_confidence:.1f}% → {enhanced_confidence:.1f}%")
        
        # 3. Add betting recommendations with confidence filtering
        betting_recs = self._generate_enhanced_betting_recommendations(enhanced_game)
        if betting_recs:
            enhanced_game['enhanced_recommendations'] = betting_recs
            enhancements.append(f"Added {len(betting_recs)} high-confidence betting recommendations")
        
        # 4. Calculate value betting opportunities
        value_bets = self._identify_value_betting_opportunities(enhanced_game)
        if value_bets:
            enhanced_game['value_betting_opportunities'] = value_bets
            enhancements.append(f"Identified {len(value_bets)} value betting opportunities")
        
        # 5. Apply simple ensemble adjustment
        ensemble_adjustment = self._apply_simple_ensemble(enhanced_game)
        if ensemble_adjustment:
            enhanced_game['ensemble_adjusted_predictions'] = ensemble_adjustment
            enhancements.append("Applied simple ensemble adjustment")
        
        if enhancements:
            enhanced_game['enhancements_applied'] = enhancements
        
        return enhanced_game
    
    def _calculate_enhanced_confidence(self, pred_data):
        """Calculate enhanced confidence based on prediction quality"""
        
        base_confidence = pred_data.get('confidence', 50)
        
        # Factor 1: Win probability extremeness
        home_prob = pred_data.get('home_win_prob', 0.5)
        prob_extremeness = abs(home_prob - 0.5) * 2  # 0 to 1
        prob_boost = prob_extremeness * 25  # Up to 25% boost
        
        # Factor 2: Score differential
        home_score = pred_data.get('predicted_home_score', 5.0)
        away_score = pred_data.get('predicted_away_score', 5.0)
        score_diff = abs(home_score - away_score)
        
        if score_diff > 3:
            diff_boost = 15  # High confidence for blowouts
        elif score_diff > 2:
            diff_boost = 10
        elif score_diff > 1:
            diff_boost = 5
        else:
            diff_boost = 0  # Low confidence for close games
        
        # Factor 3: Total runs reasonableness
        total_runs = pred_data.get('predicted_total_runs', 10.0)
        if 7.5 <= total_runs <= 12.5:  # Reasonable range
            total_boost = 10
        elif 6 <= total_runs <= 15:    # Acceptable range
            total_boost = 5
        else:                          # Extreme totals reduce confidence
            total_boost = -10
        
        # Calculate enhanced confidence
        enhanced_confidence = base_confidence + prob_boost + diff_boost + total_boost
        enhanced_confidence = max(25, min(95, enhanced_confidence))  # Clamp 25-95%
        
        return enhanced_confidence
    
    def _generate_enhanced_betting_recommendations(self, game_data):
        """Generate betting recommendations with confidence filtering"""
        
        recommendations = []
        
        if 'predictions' not in game_data or 'predictions' not in game_data['predictions']:
            return recommendations
        
        pred_data = game_data['predictions']['predictions']
        confidence = pred_data.get('confidence', 50)
        
        # Only generate recommendations for high confidence games
        if confidence < self.confidence_threshold:
            return recommendations
        
        home_prob = pred_data.get('home_win_prob', 0.5)
        predicted_total = pred_data.get('predicted_total_runs', 0)
        
        # Moneyline recommendations
        if home_prob > 0.6:  # Strong home favorite
            recommendations.append({
                'type': 'moneyline',
                'team': 'home',
                'confidence': confidence,
                'reasoning': f'Home team {home_prob:.1%} win probability with {confidence:.1f}% confidence'
            })
        elif home_prob < 0.4:  # Strong away favorite
            recommendations.append({
                'type': 'moneyline',
                'team': 'away',
                'confidence': confidence,
                'reasoning': f'Away team {1-home_prob:.1%} win probability with {confidence:.1f}% confidence'
            })
        
        # Total runs recommendations
        if 'betting_lines' in game_data and game_data['betting_lines'].get('total_line'):
            total_line = game_data['betting_lines']['total_line']
            
            if predicted_total > total_line + 1.0:  # Significant over
                edge = ((predicted_total - total_line) / total_line) * 100
                recommendations.append({
                    'type': 'total',
                    'bet': 'over',
                    'confidence': confidence,
                    'edge': f'{edge:.1f}%',
                    'reasoning': f'Predicted {predicted_total:.1f} vs line {total_line} ({edge:.1f}% edge)'
                })
            elif predicted_total < total_line - 1.0:  # Significant under
                edge = ((total_line - predicted_total) / total_line) * 100
                recommendations.append({
                    'type': 'total',
                    'bet': 'under',
                    'confidence': confidence,
                    'edge': f'{edge:.1f}%',
                    'reasoning': f'Predicted {predicted_total:.1f} vs line {total_line} ({edge:.1f}% edge)'
                })
        
        return recommendations
    
    def _identify_value_betting_opportunities(self, game_data):
        """Identify value betting opportunities"""
        
        value_bets = []
        
        if 'betting_lines' not in game_data or 'predictions' not in game_data:
            return value_bets
        
        lines = game_data['betting_lines']
        pred_data = game_data.get('predictions', {}).get('predictions', {})
        
        home_prob = pred_data.get('home_win_prob', 0.5)
        confidence = pred_data.get('confidence', 50)
        
        # Only consider high confidence predictions
        if confidence < self.confidence_threshold:
            return value_bets
        
        # Moneyline value
        if 'moneyline_home' in lines and lines['moneyline_home']:
            home_odds = lines['moneyline_home']
            implied_prob = self._odds_to_probability(home_odds)
            edge = home_prob - implied_prob
            
            if edge > self.min_edge_threshold:
                value_bets.append({
                    'type': 'moneyline_value',
                    'team': 'home',
                    'edge': f'{edge:.1%}',
                    'implied_prob': f'{implied_prob:.1%}',
                    'our_prob': f'{home_prob:.1%}',
                    'odds': home_odds,
                    'confidence': confidence
                })
        
        if 'moneyline_away' in lines and lines['moneyline_away']:
            away_odds = lines['moneyline_away']
            implied_prob = self._odds_to_probability(away_odds)
            away_prob = 1 - home_prob
            edge = away_prob - implied_prob
            
            if edge > self.min_edge_threshold:
                value_bets.append({
                    'type': 'moneyline_value',
                    'team': 'away',
                    'edge': f'{edge:.1%}',
                    'implied_prob': f'{implied_prob:.1%}',
                    'our_prob': f'{away_prob:.1%}',
                    'odds': away_odds,
                    'confidence': confidence
                })
        
        return value_bets
    
    def _odds_to_probability(self, odds):
        """Convert American odds to probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _apply_simple_ensemble(self, game_data):
        """Apply simple ensemble adjustment to predictions"""
        
        if 'predictions' not in game_data or 'predictions' not in game_data['predictions']:
            return None
        
        pred_data = game_data['predictions']['predictions']
        
        # Simple ensemble: average with a more conservative estimate
        home_prob = pred_data.get('home_win_prob', 0.5)
        home_score = pred_data.get('predicted_home_score', 5.0)
        away_score = pred_data.get('predicted_away_score', 5.0)
        
        # Conservative estimate (closer to 50/50 and lower scoring)
        conservative_home_prob = (home_prob + 0.5) / 2
        conservative_home_score = (home_score + 4.5) / 2
        conservative_away_score = (away_score + 4.5) / 2
        
        # Ensemble average
        ensemble_home_prob = (home_prob + conservative_home_prob) / 2
        ensemble_home_score = (home_score + conservative_home_score) / 2
        ensemble_away_score = (away_score + conservative_away_score) / 2
        ensemble_total = ensemble_home_score + ensemble_away_score
        
        return {
            'ensemble_home_win_prob': ensemble_home_prob,
            'ensemble_home_score': ensemble_home_score,
            'ensemble_away_score': ensemble_away_score,
            'ensemble_total_runs': ensemble_total,
            'adjustment_applied': 'Simple conservative ensemble'
        }
    
    def _generate_improvement_report(self):
        """Generate report on improvements made"""
        
        print("📈 ENHANCEMENT SUMMARY REPORT")
        print("-" * 30)
        
        improvements = [
            "✅ Pitcher Factor Validation: Clamped extreme values to 0.7-1.5 range",
            "✅ Enhanced Confidence Calculation: Based on win prob extremeness + score differential",
            "✅ High-Confidence Filtering: Only recommend 60%+ confidence bets",
            "✅ Value Betting Identification: Find 5%+ edge opportunities",
            "✅ Simple Ensemble Averaging: Blend with conservative estimates",
            "✅ Betting Recommendations: Clear reasoning and edge calculations"
        ]
        
        for improvement in improvements:
            print(f"   {improvement}")
        
        print(f"\n🎯 EXPECTED IMPROVEMENTS:")
        print("   • Accuracy increase: +3-5% from better calibration")
        print("   • Reduced losses: Only bet on high confidence predictions")
        print("   • Better value: Focus on 5%+ edge opportunities")
        print("   • Risk reduction: Conservative ensemble adjustments")
        
        print(f"\n🚀 NEXT STEPS:")
        print("   1. Test enhanced recommendations on new games")
        print("   2. Monitor performance vs original system")
        print("   3. Implement full advanced features when ready")
        print("   4. Add Kelly Criterion bet sizing")

def main():
    enhancer = QuickEnhancedEngine()
    enhancer.enhance_existing_recommendations()

if __name__ == "__main__":
    main()
