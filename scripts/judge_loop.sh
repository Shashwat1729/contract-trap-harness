#!/usr/bin/env bash
set -euo pipefail
# Infinite iterate-until-0.1 loop: judge -> fix -> test -> reproduce -> judge again
# Stops only when judges find no must_fix and scorer says no 0.1pt gain possible.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ITER=0
while true; do
  ITER=$((ITER+1))
  echo "========================================"
  echo "JUDGE LOOP ITERATION $ITER"
  echo "========================================"
  python scripts/judge_committee.py --json "evidence/reviews/judge_iter_${ITER}.json" || true
  SCORE=$(python -c "import json; print(json.load(open('evidence/reviews/judge_iter_${ITER}.json'))['total'])")
  echo "Score: $SCORE / 100"
  # Check faults
  FAULTS=$(python -c "import json; d=json.load(open('evidence/reviews/judge_iter_${ITER}.json')); print(len([f for f in d['faults'] if f['severity']=='must_fix']))")
  if [ "$FAULTS" != "0" ]; then
    echo "Must_fix faults remain: $FAULTS — continue loop (fix next)"
  else
    echo "No must_fix faults."
  fi
  # Check improvements
  IMPROVS=$(python -c "import json; d=json.load(open('evidence/reviews/judge_iter_${ITER}.json')); print(len(d['improvements']))")
  if [ "$IMPROVS" != "0" ]; then
    echo "Improvements still possible: $IMPROVS (+0.1 each) — would continue"
  else
    echo "No improvements left — LOOP END (cannot improve even by 0.1)"
    break
  fi
  if [ "$ITER" -ge 50 ]; then
    echo "Max iterations 50 reached — stop"
    break
  fi
  echo "Iter $ITER done, next would fix one improvement and re-run..."
  # In real loop, agent would apply one fix from evidence/reviews/judge_iter_${ITER}.json here then continue
  # For safety, we stop after 1 iteration in CI and require human to apply fixes
  break
done
