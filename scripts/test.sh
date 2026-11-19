#!/usr/bin/env bash
# Run backend + frontend tests (macOS / Linux).
# Usage from repo root:  ./scripts/test.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[[ -x backend/.venv/bin/python ]] || { echo "Missing backend/.venv — run ./scripts/setup.sh first" >&2; exit 1; }

echo "==> Backend pytest"
(
  cd backend
  .venv/bin/python -m pytest
)

echo "==> Frontend vitest"
(
  cd frontend
  npm test
)
