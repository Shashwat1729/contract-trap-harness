#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
echo "[baseline] starting on :$PORT"
exec python -m src.main --port "$PORT"
