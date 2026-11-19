# Run backend + frontend tests (Windows).
# Usage from repo root:  .\scripts\test.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  throw "Missing backend\.venv — run .\scripts\setup.ps1 first"
}

Write-Host "==> Backend pytest" -ForegroundColor Cyan
Push-Location (Join-Path $Root "backend")
& $venvPython -m pytest
Pop-Location

Write-Host "==> Frontend vitest" -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
npm test
Pop-Location
