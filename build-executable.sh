#!/bin/bash
set -e

echo "Building Living Storyworld executable..."

# Activate venv
source .venv/bin/activate

# Build with PyInstaller
pyinstaller \
    --name="LivingStoryworld" \
    --onefile \
    --add-data="living_storyworld/web:living_storyworld/web" \
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
    living_storyworld/__main__.py

echo ""
echo "Build complete!"
echo "Executable: dist/LivingStoryworld"
ls -lh dist/LivingStoryworld
echo ""
echo "To test: ./dist/LivingStoryworld web"
