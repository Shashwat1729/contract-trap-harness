#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8001}"
LOG="$ROOT/evidence/benchmarks/advanced_run.log"
mkdir -p "$(dirname "$LOG")"
echo "[run_advanced] PORT=$PORT LOG=$LOG"
cd "$ROOT/advanced"
PORT="$PORT" python -m src.main 2>&1 | tee "$LOG"
