#!/bin/bash

# Render build script
echo "🔧 Building MLB Betting System..."

# Print Python version for debugging
python --version

# Upgrade pip and setuptools first
pip install --upgrade pip
pip install --upgrade setuptools==69.5.1 wheel==0.41.2

# Install core dependencies first
pip install --no-cache-dir gunicorn==21.2.0
pip install --no-cache-dir Flask==2.3.3
pip install --no-cache-dir requests==2.31.0

# Install remaining requirements
pip install --no-cache-dir -r requirements.txt

# Verify gunicorn is installed
which gunicorn || echo "❌ Gunicorn not found!"
gunicorn --version || echo "❌ Gunicorn version check failed!"

echo "✅ Build complete!"
