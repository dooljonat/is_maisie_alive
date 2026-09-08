#!/usr/bin/env bash
# ismaisiealive.net — one-command startup.
# Creates/updates the venv, installs dependencies, and serves the app
# (FastAPI serves both the API and the frontend templates/static files).
set -euo pipefail
cd "$(dirname "$0")"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if [ ! -d .venv ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv .venv
fi

echo "==> Installing/updating dependencies..."
.venv/bin/pip install --upgrade -q -r requirements.txt

if [ ! -f .env ]; then
    echo "==> No .env found — copying .env.example. EDIT IT to set your admin password!"
    cp .env.example .env
fi

echo "==> Starting ismaisiealive.net on http://${HOST}:${PORT} (admin at /admin)"
exec .venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"
