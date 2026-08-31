#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE_URL="${BASELINE_URL:-http://localhost:8000}"
ADVANCED_URL="${ADVANCED_URL:-http://localhost:8001}"
echo "[eval] baseline=$BASELINE_URL advanced=$ADVANCED_URL mock=${EVAL_MOCK:-0}"
python "$ROOT/scripts/eval_harness.py"
echo "[eval] done — see evidence/benchmarks/"
