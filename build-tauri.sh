#!/bin/bash
# Build Living Storyworld desktop app with Tauri

set -e

echo "Building Living Storyworld with Tauri..."

# Activate virtual environment and install Python dependencies
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv .venv
    source .venv/bin/activate
fi

pip install -q -r requirements.txt

# Build Tauri app
cd src-tauri
cargo build --release

echo ""
echo "Build complete!"
echo "Executable: src-tauri/target/release/living-storyworld"
ls -lh target/release/living-storyworld
echo ""
echo "To test: cd src-tauri && ./target/release/living-storyworld"
