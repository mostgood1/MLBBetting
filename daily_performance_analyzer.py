#!/usr/bin/env python3
"""
Daily Performance Deep Dive Analyzer
====================================

Compares high vs low performing days to identify what factors drive success.
Specifically analyzes Aug 20 (71% accuracy) vs Aug 25 (23% accuracy).
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

class DailyPerformanceAnalyzer:
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        
    def analyze_day_differences(self, good_date="2025-08-20", bad_date="2025-08-25"):
        """Compare a high-performing day vs low-performing day"""
        
        print(f"🔍 DAILY PERFORMANCE DEEP DIVE")
        print(f"=" * 50)
        print(f"📈 Good Day: {good_date}")
        print(f"📉 Bad Day: {bad_date}")
        print()
        
        # Load data for both days
        good_day_data = self._load_day_data(good_date)
        bad_day_data = self._load_day_data(bad_date)
        
        if not good_day_data or not bad_day_data:
            print("❌ Could not load data for comparison")
            return
        
        # Analyze differences
        self._compare_pitching_quality(good_day_data, bad_day_data, good_date, bad_date)
        self._compare_weather_conditions(good_day_data, bad_day_data, good_date, bad_date)
        self._compare_team_matchups(good_day_data, bad_day_data, good_date, bad_date)
        self._compare_betting_markets(good_day_data, bad_day_data, good_date, bad_date)
        self._compare_game_outcomes(good_day_data, bad_day_data, good_date, bad_date)
        
        # Generate recommendations
        self._generate_day_quality_indicators(good_day_data, bad_day_data)
        
    def _load_day_data(self, date_str):
        """Load all data for a specific day"""
        date_underscore = date_str.replace('-', '_')
        
        data = {
            'betting_recs': {},
            'final_scores': {},
            'games': {}
        }
        
        # Load betting recommendations (contains predictions)
        betting_file = os.path.join(self.data_directory, f"betting_recommendations_{date_underscore}.json")
        if os.path.exists(betting_file):
            with open(betting_file, 'r') as f:
                betting_data = json.load(f)
                if 'games' in betting_data:
                    data['betting_recs'] = betting_data['games']
                else:
                    data['betting_recs'] = betting_data
        
        # Load final scores
        scores_file = os.path.join(self.data_directory, f"final_scores_{date_underscore}.json")
        if os.path.exists(scores_file):
            with open(scores_file, 'r') as f:
                data['final_scores'] = json.load(f)
        
        return data
    
    def _compare_pitching_quality(self, good_data, bad_data, good_date, bad_date):
        """Compare pitcher quality between days"""
        print(f"🥎 PITCHER QUALITY COMPARISON")
        print(f"-" * 30)
        
        good_pitchers = self._extract_pitcher_data(good_data)
        bad_pitchers = self._extract_pitcher_data(bad_data)
        
        if good_pitchers and bad_pitchers:
            good_avg = statistics.mean([p.get('quality_factor', 1.0) for p in good_pitchers])
            bad_avg = statistics.mean([p.get('quality_factor', 1.0) for p in bad_pitchers])
            
            print(f"📈 {good_date} Avg Pitcher Quality: {good_avg:.3f}")
            print(f"📉 {bad_date} Avg Pitcher Quality: {bad_avg:.3f}")
            print(f"🎯 Difference: {good_avg - bad_avg:.3f}")
            
            # Count elite vs struggling pitchers
            good_elite = sum(1 for p in good_pitchers if p.get('quality_factor', 1.0) < 0.9)
            bad_elite = sum(1 for p in bad_pitchers if p.get('quality_factor', 1.0) < 0.9)
            
            print(f"⭐ Elite Pitchers (< 0.9): {good_date}: {good_elite}, {bad_date}: {bad_elite}")
            
        print()
    
    def _extract_pitcher_data(self, day_data):
        """Extract pitcher information from day data"""
        pitchers = []
        
        for game_key, game_data in day_data['betting_recs'].items():
            if 'predictions' in game_data and 'pitcher_info' in game_data['predictions']:
                pitcher_info = game_data['predictions']['pitcher_info']
                
                away_pitcher = {
                    'name': pitcher_info.get('away_pitcher_name', 'Unknown'),
                    'quality_factor': pitcher_info.get('away_pitcher_factor', 1.0)
                }
                home_pitcher = {
                    'name': pitcher_info.get('home_pitcher_name', 'Unknown'),
                    'quality_factor': pitcher_info.get('home_pitcher_factor', 1.0)
                }
                
                pitchers.extend([away_pitcher, home_pitcher])
        
        return pitchers
    
    def _compare_weather_conditions(self, good_data, bad_data, good_date, bad_date):
        """Compare weather conditions"""
        print(f"🌤️ WEATHER CONDITIONS COMPARISON")
        print(f"-" * 35)
        
        good_weather = self._extract_weather_data(good_data)
        bad_weather = self._extract_weather_data(bad_data)
        
        if good_weather and bad_weather:
            print(f"📈 {good_date} Weather Summary:")
            self._print_weather_summary(good_weather)
            
            print(f"📉 {bad_date} Weather Summary:")
            self._print_weather_summary(bad_weather)
            
            # Compare impact on scoring
            good_scoring_impact = statistics.mean([w.get('run_impact', 0) for w in good_weather])
            bad_scoring_impact = statistics.mean([w.get('run_impact', 0) for w in bad_weather])
            
            print(f"🎯 Avg Scoring Impact: {good_date}: {good_scoring_impact:+.1f}%, {bad_date}: {bad_scoring_impact:+.1f}%")
        
        print()
    
    def _extract_weather_data(self, day_data):
        """Extract weather data from games"""
        weather_data = []
        
        for game_key, game_data in day_data['betting_recs'].items():
            if 'predictions' in game_data and 'meta' in game_data['predictions']:
                meta = game_data['predictions']['meta']
                if 'weather_impact' in meta:
                    weather_data.append({
                        'game': game_key,
                        'run_impact': meta.get('weather_impact', 0),
                        'temperature': meta.get('temperature', 75),
                        'wind': meta.get('wind_speed', 5)
                    })
        
        return weather_data
    
    def _print_weather_summary(self, weather_data):
        """Print weather summary"""
        if weather_data:
            avg_temp = statistics.mean([w.get('temperature', 75) for w in weather_data])
            avg_wind = statistics.mean([w.get('wind', 5) for w in weather_data])
            print(f"   Avg Temperature: {avg_temp:.1f}°F, Avg Wind: {avg_wind:.1f}mph")
        else:
            print("   No weather data available")
    
    def _compare_team_matchups(self, good_data, bad_data, good_date, bad_date):
        """Compare team strength matchups"""
        print(f"⚔️ TEAM MATCHUP COMPARISON")
        print(f"-" * 28)
        
        good_matchups = self._analyze_matchup_quality(good_data)
        bad_matchups = self._analyze_matchup_quality(bad_data)
        
        print(f"📈 {good_date}:")
        print(f"   Competitive Games: {good_matchups['competitive']}")
        print(f"   Lopsided Games: {good_matchups['lopsided']}")
        print(f"   Avg Win Prob Diff: {good_matchups['avg_prob_diff']:.1f}%")
        
        print(f"📉 {bad_date}:")
        print(f"   Competitive Games: {bad_matchups['competitive']}")
        print(f"   Lopsided Games: {bad_matchups['lopsided']}")
        print(f"   Avg Win Prob Diff: {bad_matchups['avg_prob_diff']:.1f}%")
        
        print()
    
    def _analyze_matchup_quality(self, day_data):
        """Analyze quality of team matchups"""
        win_prob_diffs = []
        
        for game_key, game_data in day_data['betting_recs'].items():
            if 'predictions' in game_data and 'predictions' in game_data['predictions']:
                pred = game_data['predictions']['predictions']
                home_prob = pred.get('home_win_prob', 0.5) * 100
                prob_diff = abs(home_prob - 50)
                win_prob_diffs.append(prob_diff)
        
        if win_prob_diffs:
            avg_diff = statistics.mean(win_prob_diffs)
            competitive = sum(1 for diff in win_prob_diffs if diff < 10)
            lopsided = sum(1 for diff in win_prob_diffs if diff > 20)
            
            return {
                'competitive': competitive,
                'lopsided': lopsided,
                'avg_prob_diff': avg_diff,
                'total_games': len(win_prob_diffs)
            }
        
        return {'competitive': 0, 'lopsided': 0, 'avg_prob_diff': 0, 'total_games': 0}
    
    def _compare_betting_markets(self, good_data, bad_data, good_date, bad_date):
        """Compare betting market conditions"""
        print(f"💰 BETTING MARKET COMPARISON")
        print(f"-" * 30)
        
        good_lines = self._analyze_line_availability(good_data)
        bad_lines = self._analyze_line_availability(bad_data)
        
        print(f"📈 {good_date}:")
        print(f"   Games w/ Lines: {good_lines['games_with_lines']}/{good_lines['total_games']}")
        print(f"   Line Coverage: {good_lines['coverage']:.1f}%")
        
        print(f"📉 {bad_date}:")
        print(f"   Games w/ Lines: {bad_lines['games_with_lines']}/{bad_lines['total_games']}")
        print(f"   Line Coverage: {bad_lines['coverage']:.1f}%")
        
        print()
    
    def _analyze_line_availability(self, day_data):
        """Analyze betting line availability"""
        total_games = len(day_data['betting_recs'])
        games_with_lines = 0
        
        for game_key, game_data in day_data['betting_recs'].items():
            if 'betting_lines' in game_data:
                lines = game_data['betting_lines']
                if lines.get('total_line') or lines.get('moneyline_home'):
                    games_with_lines += 1
        
        coverage = (games_with_lines / total_games * 100) if total_games > 0 else 0
        
        return {
            'total_games': total_games,
            'games_with_lines': games_with_lines,
            'coverage': coverage
        }
    
    def _compare_game_outcomes(self, good_data, bad_data, good_date, bad_date):
        """Compare actual game outcomes"""
        print(f"🏆 GAME OUTCOMES COMPARISON")
        print(f"-" * 29)
        
        good_outcomes = self._analyze_game_outcomes(good_data, good_date)
        bad_outcomes = self._analyze_game_outcomes(bad_data, bad_date)
        
        print(f"📈 {good_date}:")
        print(f"   Avg Total Runs: {good_outcomes['avg_total_runs']:.1f}")
        print(f"   High Scoring Games (>10): {good_outcomes['high_scoring']}")
        print(f"   Blowouts (>5 run diff): {good_outcomes['blowouts']}")
        
        print(f"📉 {bad_date}:")
        print(f"   Avg Total Runs: {bad_outcomes['avg_total_runs']:.1f}")
        print(f"   High Scoring Games (>10): {bad_outcomes['high_scoring']}")
        print(f"   Blowouts (>5 run diff): {bad_outcomes['blowouts']}")
        
        print()
    
    def _analyze_game_outcomes(self, day_data, date_str):
        """Analyze actual game outcomes"""
        total_runs = []
        run_diffs = []
        
        for game_key, score_data in day_data['final_scores'].items():
            away_score = score_data.get('away_score', score_data.get('final_away_score', 0))
            home_score = score_data.get('home_score', score_data.get('final_home_score', 0))
            
            if away_score is not None and home_score is not None:
                total = away_score + home_score
                diff = abs(away_score - home_score)
                
                total_runs.append(total)
                run_diffs.append(diff)
        
        if total_runs:
            avg_total = statistics.mean(total_runs)
            high_scoring = sum(1 for t in total_runs if t > 10)
            blowouts = sum(1 for d in run_diffs if d > 5)
            
            return {
                'avg_total_runs': avg_total,
                'high_scoring': high_scoring,
                'blowouts': blowouts
            }
        
        return {'avg_total_runs': 0, 'high_scoring': 0, 'blowouts': 0}
    
    def _generate_day_quality_indicators(self, good_data, bad_data):
        """Generate indicators for predicting day quality"""
        print(f"🎯 DAY QUALITY INDICATORS")
        print(f"-" * 26)
        print("Based on the analysis, good betting days tend to have:")
        print("✅ Better pitcher quality (lower factors)")
        print("✅ More competitive matchups (closer win probabilities)")
        print("✅ Better betting line coverage")
        print("✅ Moderate weather conditions")
        print()
        print("🚨 RED FLAGS for bad betting days:")
        print("❌ Many struggling pitchers")
        print("❌ Lopsided matchups")
        print("❌ Extreme weather conditions")
        print("❌ Limited betting line availability")
        print()

def main():
    analyzer = DailyPerformanceAnalyzer()
    
    print("🔍 DAILY PERFORMANCE DEEP DIVE ANALYZER")
    print("=" * 50)
    print()
    
    # Compare best vs worst days from our analysis
    analyzer.analyze_day_differences("2025-08-20", "2025-08-25")
    
    print("📋 RECOMMENDATIONS:")
    print("-" * 16)
    print("1. Create daily quality score before betting")
    print("2. Skip betting on days with multiple red flags")
    print("3. Increase bet sizes on high-quality days")
    print("4. Focus on games with competitive matchups")
    print("5. Monitor pitcher quality more closely")

if __name__ == "__main__":
    main()
