"""
Configuration manager for automated closing lines fetching
Helps set up API keys and configure timing parameters
"""

import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class ClosingLinesConfig:
    """Manages configuration for automated closing lines fetching"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.config_file = self.data_dir / "closing_lines_config.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        self.config = self.load_or_create_config()
    
    def load_or_create_config(self) -> Dict:
        """Load existing config or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                print(f"Loaded existing config from {self.config_file}")
                return config
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Create default config
        default_config = {
            "api_keys": {
                "odds_api_key": "",
                "pinnacle_username": "",
                "pinnacle_password": "",
                "the_odds_api_key": ""
            },
            "fetch_timing": {
                "fetch_timing_minutes": [45, 30, 20, 15, 10, 5],
                "optimal_fetch_time": 20,
                "max_attempts_per_timing": 3,
                "enable_backup_sources": True
            },
            "data_quality": {
                "prefer_pinnacle": True,
                "minimum_line_confidence": 0.8,
                "require_moneyline": True,
                "require_total": False,
                "require_spread": False
            },
            "alerts": {
                "enable_email_alerts": False,
                "enable_log_alerts": True,
                "alert_on_fetch_failure": True,
                "alert_on_api_error": True
            },
            "storage": {
                "backup_on_update": True,
                "max_backup_files": 10,
                "compress_old_data": False
            },
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        self.save_config(default_config)
        print(f"Created default config at {self.config_file}")
        return default_config
    
    def save_config(self, config: Dict = None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        config['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def update_api_keys(self, odds_api_key: str = "", pinnacle_username: str = "", 
                       pinnacle_password: str = ""):
        """Update API credentials"""
        # Ensure api_keys section exists
        if 'api_keys' not in self.config:
            self.config['api_keys'] = {}
        
        if odds_api_key:
            self.config['api_keys']['odds_api_key'] = odds_api_key
            print("Updated OddsAPI key")
        
        if pinnacle_username:
            self.config['api_keys']['pinnacle_username'] = pinnacle_username
            print("Updated Pinnacle username")
        
        if pinnacle_password:
            self.config['api_keys']['pinnacle_password'] = pinnacle_password
            print("Updated Pinnacle password")
        
        self.save_config()
    
    def update_fetch_timing(self, minutes_before: List[int] = None, 
                           optimal_time: int = None):
        """Update fetch timing configuration"""
        # Ensure fetch_timing section exists
        if 'fetch_timing' not in self.config:
            self.config['fetch_timing'] = {}
        
        if minutes_before:
            self.config['fetch_timing']['fetch_timing_minutes'] = minutes_before
            print(f"Updated fetch timing to: {minutes_before} minutes before game")
        
        if optimal_time:
            self.config['fetch_timing']['optimal_fetch_time'] = optimal_time
            print(f"Updated optimal fetch time to: {optimal_time} minutes before game")
        
        self.save_config()
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate configuration and return issues"""
        issues = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Check API keys
        api_keys = self.config.get('api_keys', {})
        if not api_keys.get('odds_api_key') and not (api_keys.get('pinnacle_username') and api_keys.get('pinnacle_password')):
            issues['errors'].append("No API credentials configured - need either OddsAPI key or Pinnacle credentials")
        
        if not api_keys.get('odds_api_key'):
            issues['warnings'].append("OddsAPI key not configured - will rely on Pinnacle or manual estimation")
        
        if not (api_keys.get('pinnacle_username') and api_keys.get('pinnacle_password')):
            issues['warnings'].append("Pinnacle credentials not configured - will rely on OddsAPI or manual estimation")
        
        # Check fetch timing
        fetch_timing = self.config.get('fetch_timing', {})
        minutes_list = fetch_timing.get('fetch_timing_minutes', [])
        
        if not minutes_list:
            issues['warnings'].append("No fetch timing configured - will use defaults [45, 30, 20, 15, 10, 5]")
        elif min(minutes_list) < 5:
            issues['warnings'].append("Fetching less than 5 minutes before game may not capture true closing lines")
        elif max(minutes_list) > 120:
            issues['warnings'].append("Fetching more than 2 hours before game will not be closing lines")
        
        # Check data quality requirements
        data_quality = self.config.get('data_quality', {})
        if data_quality.get('require_moneyline', True):
            issues['info'].append("Moneyline required for all fetches")
        if data_quality.get('require_total', False):
            issues['info'].append("Total line required for all fetches")
        if data_quality.get('require_spread', False):
            issues['info'].append("Spread line required for all fetches")
        
        return issues
    
    def print_status(self):
        """Print current configuration status"""
        print("\n=== Closing Lines Configuration Status ===")
        
        # API Status
        api_keys = self.config.get('api_keys', {})
        print(f"API Keys:")
        print(f"  OddsAPI: {'✓ Configured' if api_keys.get('odds_api_key') else '✗ Not configured'}")
        print(f"  Pinnacle: {'✓ Configured' if (api_keys.get('pinnacle_username') and api_keys.get('pinnacle_password')) else '✗ Not configured'}")
        
        # Timing Status
        fetch_timing = self.config.get('fetch_timing', {})
        minutes_list = fetch_timing.get('fetch_timing_minutes', [])
        print(f"\nFetch Timing:")
        print(f"  Scheduled fetches: {minutes_list} minutes before game")
        print(f"  Optimal timing: {fetch_timing.get('optimal_fetch_time', 20)} minutes before game")
        
        # Data Quality
        data_quality = self.config.get('data_quality', {})
        print(f"\nData Quality:")
        print(f"  Prefer Pinnacle: {data_quality.get('prefer_pinnacle', True)}")
        print(f"  Require moneyline: {data_quality.get('require_moneyline', True)}")
        print(f"  Require total: {data_quality.get('require_total', False)}")
        print(f"  Require spread: {data_quality.get('require_spread', False)}")
        
        # Validation
        issues = self.validate_config()
        if issues['errors']:
            print(f"\n❌ Errors:")
            for error in issues['errors']:
                print(f"  - {error}")
        
        if issues['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in issues['warnings']:
                print(f"  - {warning}")
        
        if issues['info']:
            print(f"\nℹ️  Info:")
            for info in issues['info']:
                print(f"  - {info}")
        
        print(f"\nConfig file: {self.config_file}")
        print(f"Last updated: {self.config.get('last_updated', 'Unknown')}")

def setup_wizard():
    """Interactive setup wizard for closing lines configuration"""
    print("=== Closing Lines Fetcher Setup Wizard ===\n")
    
    config_manager = ClosingLinesConfig()
    
    print("This wizard will help you configure the automated closing lines fetcher.")
    print("You'll need API credentials from at least one of these sources:")
    print("1. The Odds API (https://the-odds-api.com/)")
    print("2. Pinnacle API (https://pinnacle.com/)")
    print()
    
    # API Keys setup
    setup_apis = input("Do you want to configure API keys now? (y/n): ").lower().strip()
    if setup_apis == 'y':
        print("\n--- API Configuration ---")
        
        # OddsAPI
        odds_api_key = input("Enter your OddsAPI key (or press Enter to skip): ").strip()
        
        # Pinnacle
        pinnacle_username = input("Enter your Pinnacle username (or press Enter to skip): ").strip()
        pinnacle_password = ""
        if pinnacle_username:
            pinnacle_password = input("Enter your Pinnacle password: ").strip()
        
        if odds_api_key or (pinnacle_username and pinnacle_password):
            config_manager.update_api_keys(
                odds_api_key=odds_api_key,
                pinnacle_username=pinnacle_username,
                pinnacle_password=pinnacle_password
            )
            print("✓ API credentials updated")
        else:
            print("⚠️  No API credentials provided - you can add them later")
    
    # Timing setup
    setup_timing = input("\nDo you want to customize fetch timing? (y/n): ").lower().strip()
    if setup_timing == 'y':
        print("\n--- Timing Configuration ---")
        print("Current default: Fetch at 45, 30, 20, 15, 10, 5 minutes before game")
        
        custom_timing = input("Enter custom timing in minutes (comma-separated, e.g., '30,20,15,10'): ").strip()
        if custom_timing:
            try:
                minutes_list = [int(x.strip()) for x in custom_timing.split(',')]
                config_manager.update_fetch_timing(minutes_before=minutes_list)
                print("✓ Fetch timing updated")
            except ValueError:
                print("❌ Invalid timing format, keeping defaults")
    
    # Final status
    print("\n=== Setup Complete ===")
    config_manager.print_status()
    
    return config_manager

def main():
    """Main function for configuration management"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'setup':
            setup_wizard()
        elif command == 'status':
            config_manager = ClosingLinesConfig()
            config_manager.print_status()
        elif command == 'validate':
            config_manager = ClosingLinesConfig()
            issues = config_manager.validate_config()
            print("Configuration validation:")
            print(f"Errors: {len(issues['errors'])}")
            print(f"Warnings: {len(issues['warnings'])}")
            print(f"Info: {len(issues['info'])}")
        else:
            print("Usage: python closing_lines_config.py [setup|status|validate]")
    else:
        print("Closing Lines Configuration Manager")
        print("Usage: python closing_lines_config.py [setup|status|validate]")

if __name__ == "__main__":
    main()
