#!/bin/bash
# Smoke test for Living Storyworld executable
# Tests basic functionality without requiring API keys

set -e

EXECUTABLE=$(realpath "$1")
TEMP_DIR=$(mktemp -d)

echo "🧪 Running smoke tests on: $EXECUTABLE"
echo "📁 Test directory: $TEMP_DIR"

# Test 1: Help command
echo "Test 1: --help command"
"$EXECUTABLE" --help > /dev/null
echo "✅ Help command works"

# Test 2: Init command (create test world)
echo "Test 2: init command"
cd "$TEMP_DIR"
"$EXECUTABLE" init --title "Test World" --theme "A test world" --style storybook-ink > /dev/null
echo "✅ Init command works"

# Test 3: Info command (list worlds)
echo "Test 3: info command"
"$EXECUTABLE" info > /dev/null
echo "✅ Info command works"

# Test 4: World exists check
echo "Test 4: Verify world was created"
if [ ! -d "worlds/test-world" ]; then
    echo "❌ World directory not created"
    exit 1
fi
echo "✅ World directory created"

# Test 5: Config file exists
echo "Test 5: Verify config file"
if [ ! -f "worlds/test-world/config.json" ]; then
    echo "❌ Config file not created"
    exit 1
fi
echo "✅ Config file created"

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo ""
echo "✅ All smoke tests passed!"
