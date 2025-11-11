# Smoke test for Living Storyworld executable (Windows)
# Tests basic functionality without requiring API keys

param(
    [Parameter(Mandatory=$true)]
    [string]$Executable
)

$ErrorActionPreference = "Stop"

$TempDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName()))

Write-Host "🧪 Running smoke tests on: $Executable"
Write-Host "📁 Test directory: $TempDir"

try {
    # Test 1: Help command
    Write-Host "Test 1: --help command"
    & $Executable --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Help command failed" }
    Write-Host "✅ Help command works"

    # Test 2: Init command (create test world)
    Write-Host "Test 2: init command"
    Push-Location $TempDir
    & $Executable init --title "Test World" --theme "A test world" --style storybook-ink --preset cozy-adventure | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Init command failed" }
    Write-Host "✅ Init command works"

    # Test 3: Info command (list worlds)
    Write-Host "Test 3: info command"
    & $Executable info --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Info command failed" }
    Write-Host "✅ Info command works"

    # Test 4: World exists check
    Write-Host "Test 4: Verify world was created"
    if (-not (Test-Path "worlds\test-world")) {
        throw "World directory not created"
    }
    Write-Host "✅ World directory created"

    # Test 5: Config file exists
    Write-Host "Test 5: Verify config file"
    if (-not (Test-Path "worlds\test-world\config.json")) {
        throw "Config file not created"
    }
    Write-Host "✅ Config file created"

    Write-Host ""
    Write-Host "✅ All smoke tests passed!"
}
finally {
    Pop-Location
    Remove-Item -Recurse -Force $TempDir
}
