# CI/CD Setup

## Overview

Living Storyworld now has automated testing and release workflows using GitHub Actions.

## Workflows

### 1. Test Workflow (`.github/workflows/test.yml`)

**Triggers:** Every push to main, every pull request

**What it does:**
- Runs on Python 3.11 and 3.12
- Installs dependencies
- Runs pytest test suite (30 tests)
- Generates coverage report (Python 3.12 only)
- Uploads coverage HTML report as artifact

**Status:** ✅ Required check for PRs

### 2. Release Workflow (`.github/workflows/release.yml`)

**Triggers:** Git tags starting with `v*` (e.g., `v0.1.0`), or manual dispatch

**What it does:**

1. **Test Phase**
   - Runs full test suite
   - Must pass before building

2. **Build Phase** (runs on test success)
   - Builds PyInstaller executables for:
     - Linux x86_64
     - macOS x86_64
     - Windows x86_64
   - Runs smoke tests on each executable:
     - Tests `--help` command
     - Tests `init` command (creates test world)
     - Tests `info` command
     - Verifies world directory and config file creation

3. **Release Phase** (runs on build success)
   - Creates GitHub Release
   - Uploads executables as release assets
   - Generates release notes automatically

## Smoke Tests

Smoke tests ensure built executables work correctly without requiring API keys.

**Scripts:**
- `scripts/smoke-test.sh` (Linux/macOS)
- `scripts/smoke-test.ps1` (Windows)

**Tests:**
- Help command works
- Can create a new world
- Can list worlds
- World files are created correctly

## Test Suite

**Current Coverage:** 30 tests across 3 test files

### Test Files

1. **`tests/test_models.py`** (9 tests)
   - Dataclass serialization/deserialization
   - Character, Location, Item, Choice, Chapter
   - WorldState and WorldConfig

2. **`tests/test_storage.py`** (17 tests)
   - Slug generation and validation
   - Path traversal prevention
   - Security checks

3. **`tests/test_api.py`** (6 tests)
   - API endpoint validation
   - CORS and security headers
   - Settings and worlds endpoints

### Running Tests Locally

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=living_storyworld --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Creating a Release

1. **Ensure tests pass:**
   ```bash
   pytest tests/ -v
   ```

2. **Build locally (optional):**
   ```bash
   ./build-executable.sh
   ./scripts/smoke-test.sh dist/LivingStoryworld
   ```

3. **Create and push tag:**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. **GitHub Actions will:**
   - Run tests
   - Build executables for all platforms
   - Run smoke tests
   - Create GitHub Release
   - Upload artifacts

5. **Release is published** 🎉

## Status Badges

Add these to README.md to show CI status:

```markdown
![Tests](https://github.com/jonmartin721/living-storyworld/actions/workflows/test.yml/badge.svg)
![Release](https://github.com/jonmartin721/living-storyworld/actions/workflows/release.yml/badge.svg)
```

## Troubleshooting

### Test Failures

- Check test output in GitHub Actions
- Run tests locally to reproduce
- Fix failing tests before merging

### Build Failures

- Check PyInstaller output
- Verify all imports are included
- Test smoke tests locally

### Smoke Test Failures

- Verify executable runs on target platform
- Check that commands work without API keys
- Review smoke test output

## Future Improvements

- [ ] Increase test coverage to 60%+
- [ ] Add integration tests with mocked providers
- [ ] Add linting workflow (ruff)
- [ ] Add type checking (mypy)
- [ ] Add performance regression tests
- [ ] Cross-platform build verification
