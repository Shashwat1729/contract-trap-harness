#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8000}"
LOG="$ROOT/evidence/benchmarks/baseline_run.log"
mkdir -p "$(dirname "$LOG")"
echo "[run_baseline] PORT=$PORT LOG=$LOG"
cd "$ROOT/baseline"
PORT="$PORT" python -m src.main 2>&1 | tee "$LOG"
