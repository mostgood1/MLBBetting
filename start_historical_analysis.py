"""
Start Historical Analysis App with Fixed Port
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set the port environment variable
os.environ['HISTORICAL_PORT'] = '5002'
os.environ['FLASK_ENV'] = 'development'

# Import and run the historical analysis app
if __name__ == '__main__':
    try:
        from historical_analysis_app import app, logger, historical_analyzer
        
        print("🎯 Starting Historical Analysis with Fixed Configuration")
        print("=" * 60)
        
        if historical_analyzer:
            try:
                available_dates = historical_analyzer.get_available_dates()
                print(f"✅ Historical data ready: {len(available_dates)} dates available")
            except Exception as e:
                print(f"⚠️ Historical analyzer warning: {e}")
        
        port = 5002
        print(f"🚀 Starting on http://localhost:{port}")
        print(f"🔍 Health check: http://localhost:{port}/health")
        print(f"📊 Main interface: http://localhost:{port}/")
        
        # Run without debug mode to avoid restarts
        app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()
