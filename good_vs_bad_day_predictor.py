#!/usr/bin/env python3
"""
Good vs Bad Day Predictor
========================

Builds a predictive model to identify whether tomorrow will be a good betting day.
Uses historical patterns to predict daily performance before placing bets.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class GoodVsBadDayPredictor:
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        self.historical_patterns = {}
        
    def build_day_quality_predictor(self):
        """Build a predictive model for day quality"""
        
        print("🔮 GOOD vs BAD DAY PREDICTOR")
        print("=" * 32)
        print()
        
        # Load historical data and extract features
        self._load_historical_features()
        
        # Identify patterns in good vs bad days
        self._analyze_predictive_patterns()
        
        # Build scoring system
        self._create_day_quality_score()
        
        # Test predictor accuracy
        self._test_predictor_accuracy()
        
        # Generate daily betting recommendations
        self._generate_betting_calendar()
    
    def _load_historical_features(self):
        """Load features that might predict day quality"""
        
        print("📊 LOADING HISTORICAL FEATURES")
        print("-" * 31)
        
        # Find all available dates
        betting_files = []
        for file in os.listdir(self.data_directory):
            if file.startswith('betting_recommendations_2025') and file.endswith('.json'):
                betting_files.append(file)
        
        daily_features = {}
        
        for file in sorted(betting_files):
            date_str = file.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            
            features = self._extract_day_features(date_str)
            if features:
                daily_features[date_str] = features
        
        self.daily_features = daily_features
        print(f"✅ Loaded features for {len(daily_features)} days")
        print()
    
    def _extract_day_features(self, date_str):
        """Extract predictive features for a single day"""
        
        date_underscore = date_str.replace('-', '_')
        
        # Load betting recommendations
        betting_file = os.path.join(self.data_directory, f"betting_recommendations_{date_underscore}.json")
        if not os.path.exists(betting_file):
            return None
        
        # Load final scores for performance calculation
        scores_file = os.path.join(self.data_directory, f"final_scores_{date_underscore}.json")
        
        with open(betting_file, 'r') as f:
            betting_data = json.load(f)
        
        scores_data = {}
        if os.path.exists(scores_file):
            with open(scores_file, 'r') as f:
                scores_data = json.load(f)
        
        if 'games' not in betting_data:
            return None
        
        features = {
            'date': date_str,
            'total_games': len(betting_data['games']),
            'avg_pitcher_quality': 0,
            'elite_pitcher_count': 0,
            'struggling_pitcher_count': 0,
            'competitive_games': 0,
            'lopsided_games': 0,
            'avg_confidence': 0,
            'high_confidence_bets': 0,
            'weather_impact': 0,
            'line_coverage': 0,
            'avg_total_predicted': 0,
            'performance_score': 0,  # Will calculate actual performance
            'day_of_week': self._get_day_of_week(date_str),
            'is_weekend': self._is_weekend(date_str)
        }
        
        pitcher_qualities = []
        confidences = []
        total_predictions = []
        games_with_lines = 0
        correct_predictions = 0
        total_evaluatable = 0
        
        for game_key, game_data in betting_data['games'].items():
            
            # Extract pitcher quality
            if 'predictions' in game_data and 'pitcher_info' in game_data['predictions']:
                pitcher_info = game_data['predictions']['pitcher_info']
                
                away_factor = pitcher_info.get('away_pitcher_factor', 1.0)
                home_factor = pitcher_info.get('home_pitcher_factor', 1.0)
                
                pitcher_qualities.extend([away_factor, home_factor])
                
                if away_factor < 0.9:
                    features['elite_pitcher_count'] += 1
                elif away_factor > 1.3:
                    features['struggling_pitcher_count'] += 1
                
                if home_factor < 0.9:
                    features['elite_pitcher_count'] += 1
                elif home_factor > 1.3:
                    features['struggling_pitcher_count'] += 1
            
            # Extract predictions and confidence
            if 'predictions' in game_data and 'predictions' in game_data['predictions']:
                pred = game_data['predictions']['predictions']
                
                total_pred = pred.get('predicted_total_runs', 0)
                if total_pred > 0:
                    total_predictions.append(total_pred)
                
                confidence = pred.get('confidence', 50)
                confidences.append(confidence)
                
                if confidence > 70:
                    features['high_confidence_bets'] += 1
                
                # Calculate competitiveness
                home_prob = pred.get('home_win_prob', 0.5) * 100
                prob_diff = abs(home_prob - 50)
                
                if prob_diff < 10:
                    features['competitive_games'] += 1
                elif prob_diff > 20:
                    features['lopsided_games'] += 1
            
            # Check line availability
            if 'betting_lines' in game_data:
                lines = game_data['betting_lines']
                if lines.get('total_line') or lines.get('moneyline_home'):
                    games_with_lines += 1
            
            # Calculate actual performance if scores available
            if scores_data:
                actual_correct = self._check_prediction_accuracy(game_key, game_data, scores_data)
                if actual_correct is not None:
                    total_evaluatable += 1
                    if actual_correct:
                        correct_predictions += 1
        
        # Calculate aggregate features
        if pitcher_qualities:
            features['avg_pitcher_quality'] = statistics.mean(pitcher_qualities)
        
        if confidences:
            features['avg_confidence'] = statistics.mean(confidences)
        
        if total_predictions:
            features['avg_total_predicted'] = statistics.mean(total_predictions)
        
        features['line_coverage'] = (games_with_lines / features['total_games']) * 100
        
        # Calculate actual performance score
        if total_evaluatable > 0:
            features['performance_score'] = (correct_predictions / total_evaluatable) * 100
        
        return features
    
    def _check_prediction_accuracy(self, game_key, game_data, scores_data):
        """Check if prediction was accurate"""
        
        # Find actual score
        actual_total = self._find_actual_total(game_key, scores_data)
        if actual_total is None:
            return None
        
        # Get prediction
        if 'predictions' in game_data and 'predictions' in game_data['predictions']:
            pred = game_data['predictions']['predictions']
            
            predicted_home = pred.get('predicted_home_score', 0)
            predicted_away = pred.get('predicted_away_score', 0)
            
            if predicted_home > predicted_away:
                predicted_winner = 'home'
            else:
                predicted_winner = 'away'
            
            # Find actual winner
            for score_key, score_data in scores_data.items():
                if game_key in score_key or any(team in score_key for team in game_key.split('_vs_')):
                    home_score = score_data.get('home_score', score_data.get('final_home_score', 0))
                    away_score = score_data.get('away_score', score_data.get('final_away_score', 0))
                    
                    if home_score > away_score:
                        actual_winner = 'home'
                    else:
                        actual_winner = 'away'
                    
                    return predicted_winner == actual_winner
        
        return None
    
    def _find_actual_total(self, game_key, scores_data):
        """Find actual total runs for a game"""
        
        for score_key, score_data in scores_data.items():
            if game_key in score_key or any(team in score_key for team in game_key.split('_vs_')):
                away = score_data.get('away_score', score_data.get('final_away_score'))
                home = score_data.get('home_score', score_data.get('final_home_score'))
                
                if away is not None and home is not None:
                    return away + home
        
        return None
    
    def _get_day_of_week(self, date_str):
        """Get day of week (0=Monday, 6=Sunday)"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.weekday()
        except:
            return 0
    
    def _is_weekend(self, date_str):
        """Check if date is weekend"""
        day_of_week = self._get_day_of_week(date_str)
        return day_of_week >= 5  # Saturday or Sunday
    
    def _analyze_predictive_patterns(self):
        """Analyze patterns that predict good vs bad days"""
        
        print("🔍 ANALYZING PREDICTIVE PATTERNS")
        print("-" * 34)
        
        if not self.daily_features:
            print("No data available")
            return
        
        # Separate good and bad days
        good_days = []
        bad_days = []
        
        for date, features in self.daily_features.items():
            if features['performance_score'] > 60:
                good_days.append(features)
            elif features['performance_score'] < 40:
                bad_days.append(features)
        
        print(f"✅ Good Days: {len(good_days)} (>60% accuracy)")
        print(f"❌ Bad Days: {len(bad_days)} (<40% accuracy)")
        print()
        
        if good_days and bad_days:
            self._compare_feature_patterns(good_days, bad_days)
        
        print()
    
    def _compare_feature_patterns(self, good_days, bad_days):
        """Compare features between good and bad days"""
        
        print("📊 FEATURE COMPARISON:")
        print("-" * 21)
        
        features_to_compare = [
            'avg_pitcher_quality',
            'elite_pitcher_count',
            'struggling_pitcher_count',
            'competitive_games',
            'high_confidence_bets',
            'line_coverage',
            'avg_total_predicted'
        ]
        
        for feature in features_to_compare:
            good_values = [day[feature] for day in good_days if day[feature] is not None]
            bad_values = [day[feature] for day in bad_days if day[feature] is not None]
            
            if good_values and bad_values:
                good_avg = statistics.mean(good_values)
                bad_avg = statistics.mean(bad_values)
                difference = good_avg - bad_avg
                
                print(f"{feature:20}: Good {good_avg:6.2f} | Bad {bad_avg:6.2f} | Diff {difference:+6.2f}")
        
        # Weekend vs weekday analysis
        good_weekend = sum(1 for day in good_days if day['is_weekend'])
        bad_weekend = sum(1 for day in bad_days if day['is_weekend'])
        
        print(f"\n📅 TIMING PATTERNS:")
        print(f"Good days on weekends: {good_weekend}/{len(good_days)} ({good_weekend/len(good_days)*100:.1f}%)")
        print(f"Bad days on weekends: {bad_weekend}/{len(bad_days)} ({bad_weekend/len(bad_days)*100:.1f}%)")
    
    def _create_day_quality_score(self):
        """Create a scoring system to predict day quality"""
        
        print("🎯 DAY QUALITY SCORING SYSTEM")
        print("-" * 31)
        
        scoring_weights = {
            'pitcher_quality_bonus': -10,  # Lower is better for pitchers
            'elite_pitcher_bonus': 5,
            'struggling_pitcher_penalty': -3,
            'competitive_game_bonus': 2,
            'lopsided_game_penalty': -1,
            'high_confidence_bonus': 8,
            'line_coverage_bonus': 0.3,
            'weekend_bonus': 5
        }
        
        print("📋 SCORING CRITERIA:")
        for criteria, weight in scoring_weights.items():
            print(f"   {criteria:25}: {weight:+3}")
        
        # Apply scoring to historical days
        day_scores = {}
        for date, features in self.daily_features.items():
            score = self._calculate_day_score(features, scoring_weights)
            day_scores[date] = {
                'score': score,
                'actual_performance': features['performance_score'],
                'features': features
            }
        
        self.day_scores = day_scores
        print(f"\n✅ Calculated scores for {len(day_scores)} days")
        print()
    
    def _calculate_day_score(self, features, weights):
        """Calculate quality score for a day"""
        
        score = 50  # Base score
        
        # Pitcher quality (lower factor is better)
        pitcher_quality = features.get('avg_pitcher_quality', 1.0)
        score += (1.0 - pitcher_quality) * weights['pitcher_quality_bonus']
        
        # Elite and struggling pitchers
        score += features.get('elite_pitcher_count', 0) * weights['elite_pitcher_bonus']
        score += features.get('struggling_pitcher_count', 0) * weights['struggling_pitcher_penalty']
        
        # Game competitiveness
        score += features.get('competitive_games', 0) * weights['competitive_game_bonus']
        score += features.get('lopsided_games', 0) * weights['lopsided_game_penalty']
        
        # Confidence and lines
        score += features.get('high_confidence_bets', 0) * weights['high_confidence_bonus']
        score += features.get('line_coverage', 0) * weights['line_coverage_bonus']
        
        # Weekend bonus
        if features.get('is_weekend', False):
            score += weights['weekend_bonus']
        
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _test_predictor_accuracy(self):
        """Test how well the predictor works on historical data"""
        
        print("🧪 PREDICTOR ACCURACY TEST")
        print("-" * 27)
        
        if not hasattr(self, 'day_scores'):
            print("No scoring data available")
            return
        
        # Categorize predictions
        correct_predictions = 0
        total_predictions = 0
        
        high_score_correct = 0
        high_score_total = 0
        low_score_correct = 0
        low_score_total = 0
        
        for date, data in self.day_scores.items():
            predicted_score = data['score']
            actual_performance = data['actual_performance']
            
            # Skip days without actual performance data
            if actual_performance == 0:
                continue
            
            total_predictions += 1
            
            # Predict good day if score > 60, bad day if score < 40
            if predicted_score > 60:
                predicted_good = True
                high_score_total += 1
                if actual_performance > 50:
                    high_score_correct += 1
            elif predicted_score < 40:
                predicted_good = False
                low_score_total += 1
                if actual_performance < 50:
                    low_score_correct += 1
            else:
                continue  # Skip neutral predictions
            
            # Check if prediction was correct
            actual_good = actual_performance > 50
            
            if predicted_good == actual_good:
                correct_predictions += 1
        
        if total_predictions > 0:
            accuracy = (correct_predictions / total_predictions) * 100
            print(f"📊 Overall Predictor Accuracy: {accuracy:.1f}% ({correct_predictions}/{total_predictions})")
            
            if high_score_total > 0:
                high_accuracy = (high_score_correct / high_score_total) * 100
                print(f"🎯 High Score Predictions: {high_accuracy:.1f}% ({high_score_correct}/{high_score_total})")
            
            if low_score_total > 0:
                low_accuracy = (low_score_correct / low_score_total) * 100
                print(f"⚠️  Low Score Predictions: {low_accuracy:.1f}% ({low_score_correct}/{low_score_total})")
        
        print()
    
    def _generate_betting_calendar(self):
        """Generate betting recommendations for upcoming days"""
        
        print("📅 BETTING CALENDAR RECOMMENDATIONS")
        print("-" * 37)
        
        if not hasattr(self, 'day_scores'):
            print("No scoring data available")
            return
        
        # Sort days by score
        sorted_days = sorted(self.day_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        print("🏆 BEST BETTING DAYS:")
        for i, (date, data) in enumerate(sorted_days[:5]):
            score = data['score']
            actual = data['actual_performance']
            print(f"   {i+1}. {date}: Score {score:.1f} (Actual: {actual:.1f}%)")
        
        print("\n📉 AVOID THESE DAYS:")
        for i, (date, data) in enumerate(sorted_days[-3:]):
            score = data['score']
            actual = data['actual_performance']
            print(f"   {i+1}. {date}: Score {score:.1f} (Actual: {actual:.1f}%)")
        
        print(f"\n🎯 BETTING STRATEGY GUIDE:")
        print("   Score 70+: MAX bet size, high confidence")
        print("   Score 55-69: NORMAL bet size")
        print("   Score 45-54: REDUCED bet size")
        print("   Score <45: SKIP betting entirely")
        
        print(f"\n📋 TOMORROW'S PREDICTION:")
        # For demo, predict next day based on patterns
        print("   [Run this system daily to get tomorrow's score]")
        print("   [Combine with real-time weather and lineup data]")

def main():
    predictor = GoodVsBadDayPredictor()
    predictor.build_day_quality_predictor()

if __name__ == "__main__":
    main()
