#!/bin/bash
set -e

echo "Building Living Storyworld executable..."

# Activate venv
source .venv/bin/activate

# Create entry point if it doesn't exist
cat > run_app.py << 'EOF'
#!/usr/bin/env python3
"""Entry point for PyInstaller executable."""
import sys
import os

if __name__ == "__main__":
    # Add the bundled package to path if running from PyInstaller
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    # Import and run the CLI
    from living_storyworld.cli import main
    sys.exit(main())
EOF

# Build with PyInstaller
pyinstaller \
    --name="LivingStoryworld" \
    --onefile \
    --windowed \
    --add-data="living_storyworld/web:living_storyworld/web" \
    --add-data="living_storyworld:living_storyworld" \
    --hidden-import=living_storyworld \
    --collect-all living_storyworld \
    run_app.py

echo ""
echo "Build complete!"
echo "Executable: dist/LivingStoryworld"
ls -lh dist/LivingStoryworld
echo ""
echo "To test: ./dist/LivingStoryworld web"
