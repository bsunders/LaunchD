#!/usr/bin/env bash
# Run the app from the repo root (creates venv with README steps first).
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
