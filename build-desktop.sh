#!/bin/bash
# Build Living Storyworld desktop app with PyInstaller

set -e

echo "Building Living Storyworld desktop app..."

# Activate virtual environment and install dependencies
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv .venv
    source .venv/bin/activate
fi

pip install -q -r requirements.txt

# Build with PyInstaller
pyinstaller LivingStoryworld.spec --clean

echo ""
echo "Build complete!"
echo "Executable: dist/LivingStoryworld"
ls -lh dist/LivingStoryworld* 2>/dev/null || ls -lh dist/
echo ""
echo "To test: ./dist/LivingStoryworld"
