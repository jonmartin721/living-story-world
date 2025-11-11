#!/bin/bash
# Local CI testing script
# Runs the same tests as GitHub Actions CI without needing Docker

set -e

echo "Running CI tests locally..."
echo ""

# Activate virtualenv
echo "→ Activating virtualenv..."
source .venv/bin/activate

# Run pytest (same as CI)
echo "→ Running pytest..."
pytest tests/ -v --tb=short

# Build with Tauri
echo ""
echo "→ Building Tauri app..."
cd src-tauri
cargo build --release
cd ..

echo ""
echo "✅ All CI tests passed locally!"
echo ""
echo "Built app: src-tauri/target/release/living-storyworld"
ls -lh src-tauri/target/release/living-storyworld
echo ""
echo "You can now safely commit and push to GitHub."
