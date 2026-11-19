#!/usr/bin/env bash
# Start API + frontend for local development (macOS / Linux).
# Usage from repo root:  ./scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[[ -f .env ]] || { echo "Missing .env — run ./scripts/setup.sh first" >&2; exit 1; }
[[ -x backend/.venv/bin/python ]] || { echo "Missing backend/.venv — run ./scripts/setup.sh first" >&2; exit 1; }

cleanup() {
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

set -a
# shellcheck disable=SC1091
source <(grep -v '^\s*#' .env | grep -E '^[A-Za-z_][A-Za-z0-9_]*=' | sed 's/\r$//')
set +a

echo "Starting Aegis..."
echo "  API       http://127.0.0.1:8000"
echo "  Frontend  http://localhost:3000"
echo "Ctrl+C stops both."
echo

(
  cd backend
  .venv/bin/python -m uvicorn app.main:app --reload --port 8000
) &
API_PID=$!

(
  cd frontend
  CI=1 npm run dev
) &
WEB_PID=$!

wait
