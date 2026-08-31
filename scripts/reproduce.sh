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

# Run baseline + advanced unit/integration (no network needed).
# advanced/ tests run from the REPO ROOT with root-relative paths, not `cd advanced`:
# several test modules (test_bm25.py, test_semantic.py, test_llm_extract.py, ...) import
# via the absolute `advanced.src...` path, which needs the repo root on sys.path, not
# advanced/ itself (advanced/pyproject.toml's pythonpath=["."] resolves relative to
# where that config file lives, not the shell's cwd). Running with `cd advanced` here
# was the exact same bug already found and fixed in run_tests_snapshot.py (CHANGELOG
# #19) but never applied to this script -- found by actually running `make reproduce`
# fresh end to end, not by inspection.
(cd baseline && python -m pytest tests -v 2>&1 | tee -a "$ROOT/$LOG") || { echo "baseline tests FAILED" | tee -a "$LOG"; exit 1; }
python -m pytest advanced/tests/unit advanced/tests/integration -v 2>&1 | tee -a "$LOG" || { echo "advanced tests FAILED" | tee -a "$LOG"; exit 1; }

echo "[reproduce] step 2b: dashboard smoke -- actually runs app/streamlit_app.py end to end (AppTest)" | tee -a "$LOG"
(EVAL_MOCK=1 python -m pytest app/tests -v 2>&1 | tee -a "$ROOT/$LOG") || { echo "dashboard smoke FAILED" | tee -a "$LOG"; exit 1; }

echo "[reproduce] step 3a: held-out generalization suite (15 fresh contracts, mock mode)" | tee -a "$LOG"
EVAL_MOCK=1 python scripts/eval_generalization.py 2>&1 | tee -a "$LOG"

echo "[reproduce] step 3b: stress suite (7 messy real-world contracts, mock mode)" | tee -a "$LOG"
EVAL_MOCK=1 python scripts/eval_stress.py 2>&1 | tee -a "$LOG"

echo "[reproduce] step 3c: PRIMARY metric — CUAD real expert ground truth (510 real contracts, not self-graded)" | tee -a "$LOG"
python scripts/eval_cuad_ground_truth.py 2>&1 | tee -a "$LOG"

echo "[reproduce] step 3d: eval harness (30-fixture suite, mock mode — no network)" | tee -a "$LOG"
EVAL_MOCK=1 python scripts/eval_harness.py 2>&1 | tee -a "$LOG"

echo "[reproduce] step 4: assert outputs exist" | tee -a "$LOG"
for f in evidence/benchmarks/results.json evidence/benchmarks/comparison.md; do
  if [ ! -f "$f" ]; then echo "MISSING $f" | tee -a "$LOG"; exit 1; fi
  echo "  ok $f ($(wc -c < "$f" 2>/dev/null || echo ?) bytes)" | tee -a "$LOG"
done

echo "[reproduce] ✅ reproducible — log at $LOG" | tee -a "$LOG"
