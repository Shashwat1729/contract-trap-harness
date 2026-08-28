#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8001}"
echo "[advanced] starting on :$PORT (features: verification,retry,fallback,cache)"
exec python -m src.main --port "$PORT"
