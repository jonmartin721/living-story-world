#!/bin/bash
# Local CI testing script
# Runs the same tests as GitHub Actions CI without needing Docker

set -e

echo "🧪 Running CI tests locally..."
echo ""

# Activate virtualenv
echo "→ Activating virtualenv..."
source .venv/bin/activate

# Run pytest (same as CI)
echo "→ Running pytest..."
pytest tests/ -v --tb=short

# Build executable with PyInstaller
echo ""
echo "→ Building executable..."
./build-executable.sh > /dev/null 2>&1

# Run smoke tests on executable
echo ""
echo "→ Running smoke tests on executable..."
./scripts/smoke-test.sh dist/LivingStoryworld

echo ""
echo "✅ All CI tests passed locally!"
echo ""
echo "You can now safely commit and push to GitHub."
