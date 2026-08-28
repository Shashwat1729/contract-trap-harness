#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="evidence/benchmarks/reproduce.log"
mkdir -p evidence/benchmarks

echo "[reproduce] $(date -u +%Y-%m-%dT%H:%M:%SZ) — Frontier Challenge reproduce" | tee "$LOG"
echo "[reproduce] host: $(uname -a 2>/dev/null || echo windows)" | tee -a "$LOG"
python --version 2>&1 | tee -a "$LOG" || true
node --version 2>&1 | tee -a "$LOG" || true

echo "[reproduce] step 1: setup" | tee -a "$LOG"
bash scripts/setup.sh 2>&1 | tee -a "$LOG"

echo "[reproduce] step 2: tests" | tee -a "$LOG"
if [ -d ".venv/Scripts" ]; then source .venv/Scripts/activate 2>/dev/null || true; fi
if [ -d ".venv/bin" ]; then source .venv/bin/activate 2>/dev/null || true; fi

# Run baseline + advanced unit/integration (no network needed)
(cd baseline && python -m pytest tests -v 2>&1 | tee -a "$ROOT/$LOG") || { echo "baseline tests FAILED" | tee -a "$LOG"; exit 1; }
(cd advanced && python -m pytest tests -v 2>&1 | tee -a "$ROOT/$LOG") || { echo "advanced tests FAILED" | tee -a "$LOG"; exit 1; }

echo "[reproduce] step 3: eval (mock mode — no network)" | tee -a "$LOG"
EVAL_MOCK=1 python scripts/eval.py 2>&1 | tee -a "$LOG"

echo "[reproduce] step 4: assert outputs exist" | tee -a "$LOG"
for f in evidence/benchmarks/results.json evidence/benchmarks/comparison.md; do
  if [ ! -f "$f" ]; then echo "MISSING $f" | tee -a "$LOG"; exit 1; fi
  echo "  ok $f ($(wc -c < "$f" 2>/dev/null || echo ?) bytes)" | tee -a "$LOG"
done

echo "[reproduce] ✅ reproducible — log at $LOG" | tee -a "$LOG"
