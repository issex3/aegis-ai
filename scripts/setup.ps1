# One-shot local setup for Aegis AI (Windows).
# Usage from repo root:  .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $Name"
  }
}

Write-Host "==> Checking prerequisites" -ForegroundColor Cyan
Require-Command python
Require-Command npm

$pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVersion -lt [version]"3.11") {
  throw "Python 3.11+ required (found $pyVersion)"
}

Write-Host "==> Environment file" -ForegroundColor Cyan
$envFile = Join-Path $Root ".env"
$example = Join-Path $Root ".env.example"
if (-not (Test-Path $envFile)) {
  Copy-Item $example $envFile
  Write-Host "Created .env from .env.example"
} else {
  Write-Host ".env already exists — leaving it alone"
}

Write-Host "==> Backend virtualenv + dependencies" -ForegroundColor Cyan
$venvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Push-Location (Join-Path $Root "backend")
  python -m venv .venv
  Pop-Location
}
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install -r (Join-Path $Root "backend\requirements.txt")

# Generate ENCRYPTION_KEY when still a placeholder
$envText = Get-Content $envFile -Raw
if ($envText -match "ENCRYPTION_KEY=replace-with-a-fernet-key" -or $envText -match "(?m)^ENCRYPTION_KEY=\s*$") {
  $key = & $venvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  $envText = [regex]::Replace($envText, "(?m)^ENCRYPTION_KEY=.*$", "ENCRYPTION_KEY=$key")
  Set-Content -Path $envFile -Value ($envText.TrimEnd() + "`n") -NoNewline
  Write-Host "Generated ENCRYPTION_KEY into .env"
}

Write-Host "==> Database migrations" -ForegroundColor Cyan
Get-Content $envFile | ForEach-Object {
  if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
    Set-Item -Path "Env:$($matches[1].Trim())" -Value $matches[2].Trim()
  }
}
Push-Location (Join-Path $Root "backend")
& $venvPython -m alembic upgrade head
Pop-Location

Write-Host "==> Frontend dependencies" -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
npm install
Pop-Location

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Start both servers with:  .\scripts\dev.ps1"
Write-Host "App will be at http://localhost:3000"
