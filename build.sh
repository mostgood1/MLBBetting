#!/bin/bash

#!/bin/bash

# Render build script for MLB Betting System
echo "🏗️ Building MLB Betting System on Render..."

# Debug Python version to ensure we're using 3.11
echo "🐍 Python version:"
python --version
python3 --version || echo "python3 not available"

# Upgrade pip for better package resolution
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install each package individually to catch any failures
echo "🔧 Installing core packages individually..."
python -m pip install gunicorn==21.2.0
python -m pip install Flask==2.3.3
python -m pip install Flask-Compress==1.13
python -m pip install requests==2.31.0
python -m pip install numpy==1.24.3
python -m pip install python-dateutil==2.8.2
python -m pip install schedule==1.2.0
python -m pip install python-dotenv==1.0.0
python -m pip install pytz==2023.3
python -m pip install psutil==5.9.5

# Verify critical packages are installed
echo "✅ Verifying package installations..."
python -c "import flask; print(f'Flask {flask.__version__} installed')"
python -c "import gunicorn; print(f'Gunicorn installed')"
python -c "import schedule; print(f'Schedule installed')"
python -c "import requests; print(f'Requests installed')"
python -c "import numpy; print(f'Numpy installed')"

# Ensure directories exist (do not overwrite data files; Render should use same data volume/artifacts as local)
echo "📁 Ensuring data directories exist (no clobber)..."
mkdir -p data data/daily_bovada logs monitoring_data static templates
for f in unified_predictions_cache.json betting_accuracy_analysis.json daily_dashboard_stats.json historical_betting_lines_cache.json system_status.json; do
	if [ ! -f "data/$f" ]; then
		echo '{}' > "data/$f"
	else
		echo "Keeping existing data/$f"
	fi
done

echo "🎯 Build completed successfully!"
