"""
Road Team Bias Correction - MLB Betting Model
============================================
Adjust model parameters to reduce over-tuning that favors road teams
"""

import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_road_team_bias():
    """Analyze current model bias and suggest corrections"""
    
    # Load current comprehensive config
    with open('data/comprehensive_optimized_config.json', 'r') as f:
        config = json.load(f)
    
    print("🔍 Current Road Team Related Parameters:")
    print("=" * 50)
    print(f"Home Field Advantage: {config.get('home_field_advantage', 'N/A')}")
    print(f"Away Field Boost: {config.get('away_field_boost', 'N/A')}")
    print(f"Base Lambda: {config.get('engine_parameters', {}).get('base_lambda', 'N/A')}")
    print(f"Team Strength Multiplier: {config.get('engine_parameters', {}).get('team_strength_multiplier', 'N/A')}")
    
    print("\n📊 Recent Performance Metrics:")
    print("=" * 50)
    if 'optimization_metadata' in config:
        metadata = config['optimization_metadata']
        print(f"Home Team Accuracy: {metadata.get('performance_metrics', {}).get('home_accuracy', 'N/A') * 100:.1f}%")
        print(f"Home Team Bias: {metadata.get('performance_metrics', {}).get('home_bias', 'N/A'):.4f}")
        print(f"Games Analyzed: {metadata.get('games_analyzed', 'N/A')}")
    
    return config

def create_balanced_config(current_config):
    """Create a more balanced configuration that reduces road team favoritism"""
    
    balanced_config = current_config.copy()
    
    print("\n⚖️ Applying Balanced Corrections:")
    print("=" * 50)
    
    # Increase home field advantage slightly (was reduced too much)
    old_hfa = balanced_config.get('home_field_advantage', 0.06)
    new_hfa = 0.08  # Middle ground between original 0.15 and current 0.06
    balanced_config['home_field_advantage'] = new_hfa
    print(f"📈 Home Field Advantage: {old_hfa:.3f} → {new_hfa:.3f}")
    
    # Reduce away field boost (may be too generous)
    old_afb = balanced_config.get('away_field_boost', 0.04)
    new_afb = 0.02  # Cut in half
    balanced_config['away_field_boost'] = new_afb
    print(f"📉 Away Field Boost: {old_afb:.3f} → {new_afb:.3f}")
    
    # Adjust engine parameters for balance
    old_lambda = 4.62  # Default from comprehensive config
    new_lambda = 4.55  # Slight reduction
    
    if 'engine_parameters' in balanced_config:
        # Slightly reduce base lambda to reduce overall scoring
        old_lambda = balanced_config['engine_parameters'].get('base_lambda', 4.62)
        balanced_config['engine_parameters']['base_lambda'] = new_lambda
        print(f"📊 Base Lambda: {old_lambda:.3f} → {new_lambda:.3f}")
        
        # Update home field advantage in engine params too
        balanced_config['engine_parameters']['home_field_advantage'] = new_hfa
    else:
        print(f"📊 Base Lambda: {old_lambda:.3f} → {new_lambda:.3f} (engine_parameters not found)")
    
    # Update metadata
    balanced_config['config_type'] = 'balanced_road_correction'
    balanced_config['created_date'] = datetime.now().isoformat()
    
    if 'optimization_metadata' not in balanced_config:
        balanced_config['optimization_metadata'] = {}
    
    balanced_config['optimization_metadata']['balance_correction'] = {
        'correction_date': datetime.now().isoformat(),
        'reason': 'Reduce road team over-favoritism',
        'changes': {
            'home_field_advantage': f"{old_hfa:.3f} → {new_hfa:.3f}",
            'away_field_boost': f"{old_afb:.3f} → {new_afb:.3f}",
            'base_lambda': f"{old_lambda:.3f} → {new_lambda:.3f}"
        }
    }
    
    return balanced_config

def main():
    """Run road team bias correction"""
    
    print("🎯 Road Team Bias Correction")
    print("=" * 60)
    
    # Analyze current bias
    current_config = analyze_road_team_bias()
    
    # Create balanced configuration
    balanced_config = create_balanced_config(current_config)
    
    # Save balanced configuration
    output_file = f'data/balanced_road_correction_config_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w') as f:
        json.dump(balanced_config, f, indent=2)
    
    print(f"\n💾 Balanced configuration saved: {output_file}")
    
    # Also update the main comprehensive config
    with open('data/comprehensive_optimized_config.json', 'w') as f:
        json.dump(balanced_config, f, indent=2)
    
    print("📝 Updated main comprehensive config with balanced parameters")
    
    print("\n✅ Road Team Bias Correction Complete!")
    print("🔄 Restart prediction engine to apply changes")
    
    return output_file

if __name__ == "__main__":
    main()
