#!/usr/bin/env python3
"""
Athletics Team Name Normalization Script
========================================
Standardizes Oakland Athletics team names across all data files to ensure consistency
and proper game matching in historical analysis.

Target Standard: "Oakland Athletics"
"""

import json
import os
import glob
from datetime import datetime

def normalize_athletics_in_json(file_path, backup=True):
    """
    Normalize Athletics team names in a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        backup (bool): Whether to create a backup before modifying
    
    Returns:
        dict: Summary of changes made
    """
    changes = {
        'file': file_path,
        'team_name_changes': 0,
        'game_key_changes': 0,
        'other_changes': 0,
        'errors': []
    }
    
    try:
        # Create backup if requested
        if backup:
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Created backup: {backup_path}")
        
        # Load JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to string for pattern replacement
        json_string = json.dumps(data, indent=2)
        original_length = len(json_string)
        
        # Normalize team names (case-insensitive replacements)
        replacements = [
            # Team name replacements
            ('"away_team": "Athletics"', '"away_team": "Oakland Athletics"'),
            ('"home_team": "Athletics"', '"home_team": "Oakland Athletics"'),
            ('"team": "Athletics"', '"team": "Oakland Athletics"'),
            
            # Game key replacements  
            ('"Athletics_vs_', '"Oakland Athletics_vs_'),
            ('"Athletics @ ', '"Oakland Athletics @ '),
            ('"@ Athletics"', '"@ Oakland Athletics"'),
            ('Athletics_vs_Minnesota Twins', 'Oakland Athletics_vs_Minnesota Twins'),
            
            # Recommendation text replacements
            ('"Athletics ML"', '"Oakland Athletics ML"'),
            ('Athletics ML', 'Oakland Athletics ML'),
            
            # Game descriptions
            ('Los Angeles Angels @ Athletics', 'Los Angeles Angels @ Oakland Athletics'),
        ]
        
        modified_string = json_string
        for old_pattern, new_pattern in replacements:
            if old_pattern in modified_string:
                count = modified_string.count(old_pattern)
                modified_string = modified_string.replace(old_pattern, new_pattern)
                
                if 'team"' in old_pattern:
                    changes['team_name_changes'] += count
                elif '_vs_' in old_pattern or ' @ ' in old_pattern:
                    changes['game_key_changes'] += count
                else:
                    changes['other_changes'] += count
                
                print(f"🔄 Replaced {count} occurrences: {old_pattern} → {new_pattern}")
        
        # Only write if changes were made
        if len(modified_string) != original_length or json_string != modified_string:
            try:
                # Validate JSON before writing
                updated_data = json.loads(modified_string)
                
                # Write updated file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, indent=2)
                
                print(f"✅ Updated: {file_path}")
                
            except json.JSONDecodeError as e:
                changes['errors'].append(f"JSON validation failed: {e}")
                print(f"❌ JSON validation failed for {file_path}: {e}")
        else:
            print(f"ℹ️  No changes needed: {file_path}")
            
    except Exception as e:
        error_msg = f"Error processing {file_path}: {e}"
        changes['errors'].append(error_msg)
        print(f"❌ {error_msg}")
    
    return changes

def normalize_all_athletics_references():
    """
    Normalize Athletics team names across all relevant data files
    """
    print("🏟️  Oakland Athletics Team Name Normalization")
    print("=" * 50)
    
    # Define file patterns to search
    file_patterns = [
        'data/*.json',
        'data/betting_*.json',
        'data/final_scores_*.json',
        'data/unified_predictions_cache.json',
        'data/comprehensive_betting_performance.json',
        'data/current_season_schedule.json'
    ]
    
    all_changes = []
    
    # Process each file pattern
    for pattern in file_patterns:
        files = glob.glob(pattern)
        for file_path in files:
            if os.path.isfile(file_path):
                print(f"\n📄 Processing: {file_path}")
                changes = normalize_athletics_in_json(file_path, backup=True)
                all_changes.append(changes)
    
    # Summary report
    print("\n📊 NORMALIZATION SUMMARY")
    print("=" * 50)
    
    total_team_changes = sum(c['team_name_changes'] for c in all_changes)
    total_game_key_changes = sum(c['game_key_changes'] for c in all_changes)
    total_other_changes = sum(c['other_changes'] for c in all_changes)
    total_errors = sum(len(c['errors']) for c in all_changes)
    
    print(f"📈 Team name changes: {total_team_changes}")
    print(f"🎯 Game key changes: {total_game_key_changes}")
    print(f"📝 Other changes: {total_other_changes}")
    print(f"❌ Errors: {total_errors}")
    
    if total_errors > 0:
        print(f"\n⚠️  ERRORS ENCOUNTERED:")
        for change in all_changes:
            if change['errors']:
                print(f"  {change['file']}:")
                for error in change['errors']:
                    print(f"    - {error}")
    
    print(f"\n✅ Normalization complete! All Athletics references should now use 'Oakland Athletics'")
    print(f"🔍 Total files processed: {len([c for c in all_changes if c['team_name_changes'] + c['game_key_changes'] + c['other_changes'] > 0])}")
    
    return all_changes

if __name__ == "__main__":
    normalize_all_athletics_references()
