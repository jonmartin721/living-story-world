#!/bin/bash
# Local build script for testing PyInstaller builds

set -e

echo "Installing PyInstaller..."
pip install pyinstaller

echo "Building standalone executable..."
pyinstaller --onefile \
  --name story \
  --add-data "living_storyworld/web:living_storyworld/web" \
  --hidden-import=living_storyworld.api.worlds \
  --hidden-import=living_storyworld.api.chapters \
  --hidden-import=living_storyworld.api.images \
  --hidden-import=living_storyworld.api.settings \
  --hidden-import=living_storyworld.api.generate \
  --hidden-import=uvicorn.logging \
  --hidden-import=uvicorn.loops \
  --hidden-import=uvicorn.loops.auto \
  --hidden-import=uvicorn.protocols \
  --hidden-import=uvicorn.protocols.http \
  --hidden-import=uvicorn.protocols.http.auto \
  --hidden-import=uvicorn.protocols.websockets \
  --hidden-import=uvicorn.protocols.websockets.auto \
  --hidden-import=uvicorn.lifespan \
  --hidden-import=uvicorn.lifespan.on \
  --collect-all textual \
  --collect-all rich \
  living_storyworld/cli.py

echo ""
echo "Build complete! Binary at: dist/story"
echo ""
echo "Test it with:"
echo "  ./dist/story --help"
echo "  ./dist/story web"
