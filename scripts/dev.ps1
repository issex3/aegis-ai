# Start API + frontend for local development (Windows).
# Usage from repo root:  .\scripts\dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$envFile = Join-Path $Root ".env"
$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $envFile)) {
  throw "Missing .env — run .\scripts\setup.ps1 first"
}
if (-not (Test-Path $venvPython)) {
  throw "Missing backend\.venv — run .\scripts\setup.ps1 first"
}

Write-Host "Starting Aegis..." -ForegroundColor Cyan
Write-Host "  API       http://127.0.0.1:8000"
Write-Host "  Frontend  http://localhost:3000"
Write-Host "Close the two PowerShell windows to stop."
Write-Host ""

$backendCmd = @"
Set-Location '$Root\backend'
Get-Content '$envFile' | ForEach-Object {
  if (`$_ -match '^\s*([^#][^=]+)=(.*)$') {
    Set-Item -Path ("Env:" + `$matches[1].Trim()) -Value `$matches[2].Trim()
  }
}
& '$venvPython' -m uvicorn app.main:app --reload --port 8000
"@

$frontendCmd = @"
Set-Location '$Root\frontend'
`$env:CI = '1'
npm run dev
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd)
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCmd)
