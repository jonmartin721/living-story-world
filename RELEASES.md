# Release Process

This document explains how to create releases with standalone binaries for Living Storyworld.

## Automated Releases via GitHub Actions

The project uses GitHub Actions to automatically build binaries for Linux, macOS, and Windows whenever you push a version tag.

### Creating a Release

1. **Update version references** (if you have a VERSION file or version in code)

2. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Prepare for release v1.0.0"
   ```

3. **Create and push a version tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin main
   git push origin v1.0.0
   ```

4. **GitHub Actions will automatically**:
   - Build binaries for Linux (x86_64)
   - Build binaries for macOS (x86_64)
   - Build binaries for Windows (x86_64)
   - Create a GitHub Release
   - Attach all binaries to the release
   - Generate release notes from commits

5. **Check the release** at: `https://github.com/YOUR_USERNAME/living-storyworld/releases`

### Manual Trigger

You can also manually trigger the release workflow from the GitHub Actions tab without creating a tag (useful for testing).

## Local Testing

Before creating a release, test the build locally:

```bash
./build_local.sh
```

This will create a standalone binary at `dist/story` that you can test:

```bash
./dist/story --help
./dist/story web
```

## Release Artifacts

Each release includes three binaries:

- **story-linux-x86_64** - Linux standalone executable
- **story-macos-x86_64** - macOS standalone executable
- **story-windows-x86_64.exe** - Windows standalone executable

Users can download and run these directly without installing Python or dependencies.

## Version Numbering

Follow semantic versioning:
- **Major** (v1.0.0): Breaking changes
- **Minor** (v0.1.0): New features, backward compatible
- **Patch** (v0.0.1): Bug fixes, backward compatible

## What Gets Bundled

The PyInstaller build includes:
- All Python code from `living_storyworld/`
- Web UI files from `living_storyworld/web/`
- All required Python dependencies
- Hidden imports for FastAPI, Uvicorn, Textual, Rich

## Troubleshooting

### Build fails on GitHub Actions

- Check the Actions tab for error logs
- Common issues:
  - Missing hidden imports (add to workflow YAML)
  - Missing data files (add via `--add-data`)
  - Platform-specific dependency issues

### Binary doesn't work

- Test locally first with `./build_local.sh`
- Check that all API keys are configured via environment variables or setup command
- Ensure the `web/` directory is properly bundled

### Missing dependencies in binary

If users report missing modules, add them as hidden imports in `.github/workflows/release.yml`:

```yaml
--hidden-import=your.missing.module
```

## Cleaning Up

PyInstaller creates build artifacts that should not be committed:

```bash
rm -rf build/ dist/ *.spec
```

These are already in `.gitignore`.
