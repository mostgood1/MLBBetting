#!/bin/bash

# Render build script
echo "🔧 Building MLB Betting System..."

# Upgrade pip and setuptools first
pip install --upgrade pip setuptools wheel

# Install requirements
pip install --no-cache-dir -r requirements.txt

echo "✅ Build complete!"
