#!/usr/bin/env python3
"""
Quick Render Cache Status Checker
Checks just the cache status to see if the fix worked
"""

import requests
import json

def quick_cache_check(base_url):
    """Quick check of cache status"""
    print(f"🔍 Checking cache status: {base_url}")
    
    try:
        # Check data status
        response = requests.get(f"{base_url}/api/debug/data-status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            cache_info = data.get('files', {}).get('unified_predictions_cache.json', {})
            cache_size = cache_info.get('size_bytes', 0)
            
            print(f"📊 Cache Status:")
            print(f"   Size: {cache_size} bytes")
            
            if cache_size <= 10:
                print("   ❌ EMPTY - Cache population failed")
                return False
            elif cache_size > 4000:
                print("   ✅ POPULATED - Cache has data!")
                
                # Quick games test
                games_response = requests.get(f"{base_url}/api/today-games", timeout=10)
                if games_response.status_code == 200:
                    games_data = games_response.json()
                    game_count = len(games_data.get('games', []))
                    print(f"   🎮 Games API: {game_count} games found")
                    return game_count > 0
                else:
                    print(f"   ⚠️ Games API failed: {games_response.status_code}")
                    return False
            else:
                print(f"   ⚠️ PARTIAL - Cache size unexpected")
                return False
                
        else:
            print(f"❌ Debug endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python quick_cache_check.py <render-url>")
        sys.exit(1)
    
    url = sys.argv[1].rstrip('/')
    success = quick_cache_check(url)
    
    if success:
        print("\n🎉 SUCCESS - Site should be working now!")
    else:
        print("\n⏳ Still processing - check Render logs or wait a few minutes")
