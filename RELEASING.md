# Creating Releases

## Building the Executable

### Linux

```bash
./build-executable.sh
```

The executable will be created at `dist/LivingStoryworld` (~50MB).

### Windows (future)

On Windows, PyInstaller will create a `.exe` file:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --name="LivingStoryworld" --onefile --windowed --add-data="living_storyworld/web;living_storyworld/web" --add-data="living_storyworld;living_storyworld" --hidden-import=living_storyworld --collect-all living_storyworld run_app.py
```

## Creating a GitHub Release

1. **Build the executable** for your platform
2. **Test the executable** to ensure it works
3. **Create a new tag**:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```
4. **Create release on GitHub**:
   - Go to Releases → Draft a new release
   - Select your tag
   - Upload `dist/LivingStoryworld` (or `dist/LivingStoryworld.exe` on Windows)
   - Name it: `LivingStoryworld-v0.1.0-linux` (or `-windows.exe`)
   - Write release notes
   - Publish

## Distribution

The executable can be distributed via:
- **GitHub Releases** - Recommended for versioned releases
- **Direct download** - Share the file directly
- **Telegram/Discord** - Upload to channels

Users can run it with:
```bash
chmod +x LivingStoryworld  # Linux only, first time
./LivingStoryworld web
```

Or double-click (if desktop environment supports it).

## Notes

- The executable is **platform-specific** (Linux binary won't run on Windows)
- Size is ~50MB on Linux, ~60-80MB on Windows
- No Python installation required for end users
- All dependencies are bundled
- Users still need to configure API keys on first run
