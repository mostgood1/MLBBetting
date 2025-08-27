#!/usr/bin/env python3
"""
MLB Bullpen Factor Integration System
===================================
Integrates bullpen statistics and performance into the prediction model
to improve accuracy for:
- Late-game situations
- Close game predictions  
- Save situations
- Bullpen quality impact on total runs
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import statistics
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BullpenFactorSystem:
    """System for integrating bullpen factors into MLB predictions"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.bullpen_file = os.path.join(data_dir, 'bullpen_stats.json')
        self.bullpen_cache_file = os.path.join(data_dir, 'bullpen_cache.json')
        
        # Bullpen impact weights
        self.weights = {
            'era_weight': 0.4,
            'whip_weight': 0.25,
            'save_rate_weight': 0.2,
            'innings_weight': 0.15,
        }
        
        # Load or initialize bullpen data
        self.bullpen_stats = self.load_bullpen_data()

    def load_bullpen_data(self) -> Dict[str, Dict]:
        """Load bullpen statistics from file or generate estimates"""
        try:
            if os.path.exists(self.bullpen_file):
                with open(self.bullpen_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load bullpen data: {e}")
        
        # Generate estimated bullpen stats
        return self.generate_estimated_bullpen_stats()

    def generate_estimated_bullpen_stats(self) -> Dict[str, Dict]:
        """Generate realistic bullpen statistics for all MLB teams"""
        
        # MLB teams with estimated bullpen performance tiers
        team_bullpen_tiers = {
            # Elite bullpens (ERA < 3.5)
            "Los Angeles Dodgers": {"tier": "elite", "era_base": 3.2},
            "Atlanta Braves": {"tier": "elite", "era_base": 3.3}, 
            "New York Yankees": {"tier": "elite", "era_base": 3.4},
            "Cleveland Guardians": {"tier": "elite", "era_base": 3.3},
            "Houston Astros": {"tier": "elite", "era_base": 3.4},
            
            # Good bullpens (ERA 3.5-4.0)
            "Tampa Bay Rays": {"tier": "good", "era_base": 3.6},
            "Baltimore Orioles": {"tier": "good", "era_base": 3.7},
            "Philadelphia Phillies": {"tier": "good", "era_base": 3.8},
            "Milwaukee Brewers": {"tier": "good", "era_base": 3.7},
            "San Diego Padres": {"tier": "good", "era_base": 3.9},
            "Toronto Blue Jays": {"tier": "good", "era_base": 3.8},
            "Minnesota Twins": {"tier": "good", "era_base": 3.9},
            "Seattle Mariners": {"tier": "good", "era_base": 3.8},
            
            # Average bullpens (ERA 4.0-4.5)
            "Boston Red Sox": {"tier": "average", "era_base": 4.1},
            "New York Mets": {"tier": "average", "era_base": 4.2},
            "St. Louis Cardinals": {"tier": "average", "era_base": 4.3},
            "Arizona Diamondbacks": {"tier": "average", "era_base": 4.1},
            "Texas Rangers": {"tier": "average", "era_base": 4.4},
            "Kansas City Royals": {"tier": "average", "era_base": 4.2},
            "Miami Marlins": {"tier": "average", "era_base": 4.3},
            "San Francisco Giants": {"tier": "average", "era_base": 4.2},
            "Pittsburgh Pirates": {"tier": "average", "era_base": 4.4},
            
            # Below-average bullpens (ERA 4.5+)
            "Chicago Cubs": {"tier": "below_average", "era_base": 4.6},
            "Detroit Tigers": {"tier": "below_average", "era_base": 4.7},
            "Washington Nationals": {"tier": "below_average", "era_base": 4.8},
            "Cincinnati Reds": {"tier": "below_average", "era_base": 4.7},
            "Los Angeles Angels": {"tier": "below_average", "era_base": 4.9},
            "Chicago White Sox": {"tier": "below_average", "era_base": 5.1},
            "Athletics": {"tier": "below_average", "era_base": 4.8},
            "Colorado Rockies": {"tier": "below_average", "era_base": 5.2},
        }
        
        bullpen_data = {}
        
        for team, info in team_bullpen_tiers.items():
            era_base = info["era_base"]
            tier = info["tier"]
            
            # Generate related stats based on ERA tier
            if tier == "elite":
                whip = 1.10 + (hash(team) % 20) / 100  # 1.10-1.30
                save_rate = 0.85 + (hash(team) % 10) / 100  # 85-95%
                innings = 480 + (hash(team) % 40)  # 480-520 IP
                blown_saves = 3 + (hash(team) % 5)  # 3-8 blown saves
            elif tier == "good":
                whip = 1.25 + (hash(team) % 20) / 100  # 1.25-1.45
                save_rate = 0.75 + (hash(team) % 15) / 100  # 75-90%
                innings = 460 + (hash(team) % 40)  # 460-500 IP
                blown_saves = 6 + (hash(team) % 8)  # 6-14 blown saves
            elif tier == "average":
                whip = 1.35 + (hash(team) % 25) / 100  # 1.35-1.60
                save_rate = 0.65 + (hash(team) % 20) / 100  # 65-85%
                innings = 450 + (hash(team) % 50)  # 450-500 IP
                blown_saves = 10 + (hash(team) % 10)  # 10-20 blown saves
            else:  # below_average
                whip = 1.45 + (hash(team) % 30) / 100  # 1.45-1.75
                save_rate = 0.55 + (hash(team) % 25) / 100  # 55-80%
                innings = 430 + (hash(team) % 60)  # 430-490 IP
                blown_saves = 15 + (hash(team) % 15)  # 15-30 blown saves
            
            # Calculate derived stats
            saves = int(save_rate * 40)  # Approximate saves based on rate
            total_save_opportunities = saves + blown_saves
            actual_save_rate = saves / total_save_opportunities if total_save_opportunities > 0 else 0.7
            
            # Calculate quality factor (0.5 to 1.5 scale)
            era_factor = max(0.5, min(1.5, 2.0 - ((era_base - 3.0) / 2.5)))
            whip_factor = max(0.5, min(1.5, 2.0 - ((whip - 1.0) / 0.8)))
            save_factor = actual_save_rate * 1.5  # Convert to 0-1.5 scale
            
            quality_factor = (era_factor * 0.5 + whip_factor * 0.3 + save_factor * 0.2)
            
            bullpen_data[team] = {
                "era": round(era_base, 2),
                "whip": round(whip, 2),
                "saves": saves,
                "blown_saves": blown_saves,
                "save_rate": round(actual_save_rate, 3),
                "innings_pitched": innings,
                "quality_factor": round(quality_factor, 3),
                "tier": tier,
                "estimated": True,
                "last_updated": datetime.now().isoformat()
            }
        
        # Save generated data
        self.save_bullpen_data(bullpen_data)
        return bullpen_data

    def save_bullpen_data(self, data: Dict[str, Dict]) -> None:
        """Save bullpen data to file"""
        try:
            with open(self.bullpen_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved bullpen data for {len(data)} teams")
        except Exception as e:
            logger.error(f"Failed to save bullpen data: {e}")

    def get_bullpen_factor(self, team_name: str) -> float:
        """Get bullpen quality factor for a team (0.5 to 1.5 scale)"""
        if team_name not in self.bullpen_stats:
            logger.warning(f"No bullpen data for {team_name}, using default factor")
            return 1.0
        
        return self.bullpen_stats[team_name].get('quality_factor', 1.0)

    def get_bullpen_era_impact(self, team_name: str) -> float:
        """Get bullpen ERA impact factor"""
        if team_name not in self.bullpen_stats:
            return 1.0
        
        era = self.bullpen_stats[team_name].get('era', 4.0)
        # Convert ERA to impact factor (lower ERA = lower opponent scoring)
        return max(0.7, min(1.3, era / 4.0))

    def get_bullpen_save_reliability(self, team_name: str) -> float:
        """Get bullpen save reliability factor (for close games)"""
        if team_name not in self.bullpen_stats:
            return 0.75  # Default 75% reliability
        
        return self.bullpen_stats[team_name].get('save_rate', 0.75)

    def calculate_bullpen_game_impact(self, home_team: str, away_team: str, 
                                    predicted_score_diff: float) -> Dict[str, float]:
        """Calculate bullpen impact on game prediction"""
        
        home_factor = self.get_bullpen_factor(home_team)
        away_factor = self.get_bullpen_factor(away_team)
        
        home_era_impact = self.get_bullpen_era_impact(home_team)
        away_era_impact = self.get_bullpen_era_impact(away_team)
        
        # Close game modifier (bullpen more important in close games)
        close_game_multiplier = max(1.0, 2.0 - abs(predicted_score_diff))
        
        # Calculate impacts
        impacts = {
            'home_bullpen_factor': home_factor,
            'away_bullpen_factor': away_factor,
            'home_scoring_modifier': 1.0 / away_era_impact,  # Away bullpen affects home scoring
            'away_scoring_modifier': 1.0 / home_era_impact,  # Home bullpen affects away scoring
            'close_game_multiplier': close_game_multiplier,
            'bullpen_advantage': (home_factor - away_factor) * close_game_multiplier * 0.1
        }
        
        return impacts

    def apply_bullpen_adjustments(self, prediction: Dict[str, Any], 
                                home_team: str, away_team: str) -> Dict[str, Any]:
        """Apply bullpen factors to existing prediction"""
        
        # Get current predictions
        home_score = prediction.get('predicted_home_score', 4.0)
        away_score = prediction.get('predicted_away_score', 4.0)
        total_score = prediction.get('predicted_total_runs', 8.0)
        home_prob = prediction.get('home_win_prob', 0.5)
        away_prob = prediction.get('away_win_prob', 0.5)
        
        # Calculate bullpen impacts
        score_diff = home_score - away_score
        impacts = self.calculate_bullpen_game_impact(home_team, away_team, score_diff)
        
        # Apply scoring modifiers
        bullpen_weight = 0.15  # 15% bullpen impact
        
        adjusted_home_score = home_score * (1 + (impacts['home_scoring_modifier'] - 1) * bullpen_weight)
        adjusted_away_score = away_score * (1 + (impacts['away_scoring_modifier'] - 1) * bullpen_weight)
        adjusted_total = adjusted_home_score + adjusted_away_score
        
        # Apply win probability adjustments
        bullpen_advantage = impacts['bullpen_advantage']
        prob_adjustment = bullpen_advantage * 0.02  # Max 2% adjustment per 0.1 bullpen advantage
        
        adjusted_home_prob = max(0.1, min(0.9, home_prob + prob_adjustment))
        adjusted_away_prob = 1.0 - adjusted_home_prob
        
        # Create adjusted prediction
        adjusted_prediction = prediction.copy()
        adjusted_prediction.update({
            'predicted_home_score': round(adjusted_home_score, 1),
            'predicted_away_score': round(adjusted_away_score, 1), 
            'predicted_total_runs': round(adjusted_total, 1),
            'home_win_prob': adjusted_home_prob,
            'away_win_prob': adjusted_away_prob,
            'bullpen_factors': {
                'home_bullpen_quality': impacts['home_bullpen_factor'],
                'away_bullpen_quality': impacts['away_bullpen_factor'],
                'bullpen_advantage': bullpen_advantage,
                'adjustments_applied': {
                    'home_score_adj': adjusted_home_score - home_score,
                    'away_score_adj': adjusted_away_score - away_score,
                    'total_adj': adjusted_total - total_score,
                    'prob_adj': prob_adjustment
                }
            }
        })
        
        return adjusted_prediction

    def get_team_bullpen_summary(self, team_name: str) -> Dict[str, Any]:
        """Get comprehensive bullpen summary for a team"""
        if team_name not in self.bullpen_stats:
            return {"error": f"No data available for {team_name}"}
        
        stats = self.bullpen_stats[team_name]
        
        # Determine rating
        quality = stats.get('quality_factor', 1.0)
        if quality >= 1.2:
            rating = "Elite"
        elif quality >= 1.05:
            rating = "Good"
        elif quality >= 0.95:
            rating = "Average"
        else:
            rating = "Below Average"
        
        return {
            'team': team_name,
            'rating': rating,
            'quality_factor': quality,
            'era': stats.get('weighted_era', stats.get('era', 4.0)),
            'whip': stats.get('weighted_whip', stats.get('whip', 1.3)),
            'save_rate': stats.get('save_rate', 0.75),
            'saves': stats.get('saves', 0),
            'blown_saves': stats.get('blown_saves', 0),
            'innings_pitched': stats.get('total_innings', stats.get('innings_pitched', 0)),
            'tier': stats.get('tier', 'unknown'),
            'estimated': stats.get('estimated', False)
        }

    def generate_bullpen_report(self) -> str:
        """Generate comprehensive bullpen analysis report"""
        
        team_rankings = []
        for team, stats in self.bullpen_stats.items():
            team_rankings.append({
                'team': team,
                'quality_factor': stats.get('quality_factor', 1.0),
                'era': stats.get('era', 0),
                'save_rate': stats.get('save_rate', 0),
                'tier': stats.get('tier', 'unknown')
            })
        
        # Sort by quality factor
        team_rankings.sort(key=lambda x: x['quality_factor'], reverse=True)
        
        report = f"""
🏟️ MLB Bullpen Analysis Report
=============================
📊 Teams Analyzed: {len(self.bullpen_stats)}
📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🏆 Top 10 Bullpens by Quality Factor:
"""
        
        for i, team in enumerate(team_rankings[:10], 1):
            report += f"  {i:2d}. {team['team']:<25} | Quality: {team['quality_factor']:.3f} | ERA: {team['era']:.2f} | Save%: {team['save_rate']:.1%}\n"
        
        report += f"""
📉 Bottom 5 Bullpens:
"""
        
        for i, team in enumerate(team_rankings[-5:], len(team_rankings)-4):
            report += f"  {i:2d}. {team['team']:<25} | Quality: {team['quality_factor']:.3f} | ERA: {team['era']:.2f} | Save%: {team['save_rate']:.1%}\n"
        
        # Tier distribution
        tier_counts = {}
        for team in team_rankings:
            tier = team['tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        report += f"""
📈 Bullpen Tier Distribution:
"""
        for tier, count in tier_counts.items():
            report += f"  • {tier.replace('_', ' ').title()}: {count} teams\n"
        
        report += f"""
⚙️ Integration Status:
  • Bullpen factors integrated into prediction model
  • Close game impact multiplier active
  • Save situation reliability tracking enabled
  • ERA-based opponent scoring adjustments applied

🎯 Expected Impact:
  • Improved accuracy in close games (±1-2 runs)
  • Better late-inning prediction reliability
  • Enhanced total runs prediction accuracy
  • More realistic win probability in tight contests
"""
        
        return report

def main():
    """Run bullpen factor system initialization"""
    print("🏟️ MLB Bullpen Factor Integration System")
    print("=" * 50)
    
    bullpen_system = BullpenFactorSystem()
    
    # Generate bullpen report
    report = bullpen_system.generate_bullpen_report()
    print(report)
    
    # Test bullpen factor calculation
    print("\n🧪 Testing Bullpen Factor Calculation")
    print("-" * 40)
    
    # Example calculation
    home_team = "Los Angeles Dodgers"
    away_team = "Chicago White Sox"
    
    home_summary = bullpen_system.get_team_bullpen_summary(home_team)
    away_summary = bullpen_system.get_team_bullpen_summary(away_team)
    
    print(f"🏠 {home_team}: {home_summary['rating']} (Quality: {home_summary['quality_factor']:.3f})")
    print(f"✈️  {away_team}: {away_summary['rating']} (Quality: {away_summary['quality_factor']:.3f})")
    
    # Test prediction adjustment
    sample_prediction = {
        'predicted_home_score': 5.2,
        'predicted_away_score': 4.1,
        'predicted_total_runs': 9.3,
        'home_win_prob': 0.58,
        'away_win_prob': 0.42
    }
    
    adjusted = bullpen_system.apply_bullpen_adjustments(sample_prediction, home_team, away_team)
    
    print(f"\n📊 Prediction Adjustment Example:")
    print(f"Original: {home_team} {sample_prediction['predicted_home_score']:.1f} - {sample_prediction['predicted_away_score']:.1f} {away_team}")
    print(f"Adjusted: {home_team} {adjusted['predicted_home_score']:.1f} - {adjusted['predicted_away_score']:.1f} {away_team}")
    print(f"Win Prob: {sample_prediction['home_win_prob']:.1%} → {adjusted['home_win_prob']:.1%}")
    print(f"Total: {sample_prediction['predicted_total_runs']:.1f} → {adjusted['predicted_total_runs']:.1f}")
    
    bullpen_adj = adjusted.get('bullpen_factors', {}).get('adjustments_applied', {})
    print(f"Bullpen Impact: Home {bullpen_adj.get('home_score_adj', 0):+.2f}, Away {bullpen_adj.get('away_score_adj', 0):+.2f}")

if __name__ == "__main__":
    main()
