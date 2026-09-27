#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--budget-ms", type=float, default=15000.0)
parser.add_argument("--results", type=str, default="evidence/benchmarks/results.json")
args = parser.parse_args()
p = Path(args.results)
if not p.exists():
    print(f"SLO SKIP: {p} not found -- run make eval first", file=sys.stderr)
    sys.exit(0)
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    lat = data.get("summary", {}).get("latency_ms", {})
    b, a = lat.get("baseline_p95"), lat.get("advanced_p95")
    if b is None or a is None:
        print(f"SLO SKIP: p95 missing (b={b}, a={a})", file=sys.stderr)
        sys.exit(0)
    delta = a - b
    budget = args.budget_ms
    print(f"SLO: baseline p95={b:.1f}ms advanced p95={a:.1f}ms delta={delta:+.1f}ms budget=+{budget:.1f}ms")
    if delta > budget:
        print(f"SLO FAIL: delta {delta:.1f}ms > budget {budget:.1f}ms", file=sys.stderr)
        sys.exit(1)
    print("SLO PASS")
    sys.exit(0)
except Exception as e:
    print(f"SLO ERROR: {e}", file=sys.stderr)
    sys.exit(1)
