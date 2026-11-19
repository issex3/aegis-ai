#!/usr/bin/env bash
# One-shot local setup for Aegis AI (macOS / Linux).
# Usage from repo root:  ./scripts/setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }; }

echo "==> Checking prerequisites"
need python3
need npm

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11+ required (found $PY_VER)" >&2
  exit 1
}

echo "==> Environment file"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo ".env already exists — leaving it alone"
fi

echo "==> Backend virtualenv + dependencies"
if [[ ! -x backend/.venv/bin/python ]]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install --upgrade pip >/dev/null
backend/.venv/bin/python -m pip install -r backend/requirements.txt

if grep -qE '^ENCRYPTION_KEY=(replace-with-a-fernet-key)?$' .env; then
  KEY="$(backend/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  # portable-ish replace of ENCRYPTION_KEY line
  tmp="$(mktemp)"
  awk -v key="$KEY" 'BEGIN{done=0} /^ENCRYPTION_KEY=/{print "ENCRYPTION_KEY=" key; done=1; next} {print} END{if(!done) print "ENCRYPTION_KEY=" key}' .env > "$tmp"
  mv "$tmp" .env
  echo "Generated ENCRYPTION_KEY into .env"
fi

echo "==> Database migrations"
set -a
# shellcheck disable=SC1091
source <(grep -v '^\s*#' .env | grep -E '^[A-Za-z_][A-Za-z0-9_]*=' | sed 's/\r$//')
set +a
(
  cd backend
  .venv/bin/python -m alembic upgrade head
)

echo "==> Frontend dependencies"
(
  cd frontend
  npm install
)

echo
echo "Setup complete."
echo "Start both servers with:  ./scripts/dev.sh"
echo "App will be at http://localhost:3000"
