#!/usr/bin/env python3
"""
Runs every real test suite in this repo and writes evidence/benchmarks/test_results.json --
a real, live snapshot the dashboard reads instead of the hardcoded pass-counts an earlier
version had baked into app/streamlit_app.py directly ("9 passed", "48 passed / 1 skipped" --
correct on the day someone typed them, silently wrong ever after). Run with `make test-snapshot`
or `python scripts/run_tests_snapshot.py` before opening the dashboard's Tests tab, or as part
of CI, so the numbers shown are never more than one run stale and are always real.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "evidence" / "benchmarks"

SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+) passed)?"
    r"(?:, (?P<failed>\d+) failed)?"
    r"(?:, (?P<skipped>\d+) skipped)?"
    r"(?:, (?P<errors>\d+) error)?"
)

SUITES = [
    ("baseline_unit", "baseline", ["tests/unit"]),
    ("baseline_integration", "baseline", ["tests/integration"]),
    # Run from repo root, not cwd=advanced: several test modules (test_semantic.py,
    # test_bm25.py, ...) import via the absolute "advanced.src..." package path (needed
    # so they can be imported the same way core.py imports itself), which only resolves
    # when the repo root is on sys.path. cwd=advanced with pyproject.toml's
    # pythonpath=["."] put advanced/ itself on the path instead, silently breaking
    # collection for every such file (ModuleNotFoundError: No module named 'advanced')
    # while still reporting a misleadingly generic "1 error" -- found by this script
    # actually failing, not by inspection.
    ("advanced_unit", None, ["advanced/tests/unit"]),
    ("advanced_integration", None, ["advanced/tests/integration"]),
    ("dashboard_smoke", None, ["app/tests"]),
    ("e2e", None, ["tests/e2e"]),
]


def _run_suite(cwd: Path, args: list[str]) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "--tb=no"],
        cwd=str(cwd), capture_output=True, text=True,
        env={**__import__("os").environ, "EVAL_MOCK": "1"},
    )
    elapsed_s = round(time.perf_counter() - t0, 2)
    out = proc.stdout + "\n" + proc.stderr
    last_line = ""
    for line in reversed(out.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line or "error" in line or "no tests ran" in line):
            last_line = line.strip()
            break
    m = SUMMARY_RE.search(last_line)
    counts = {k: int(v) if v else 0 for k, v in (m.groupdict() if m else {}).items()}
    return {
        "raw_summary_line": last_line or out.strip()[-300:],
        "counts": counts,
        "returncode": proc.returncode,
        "elapsed_s": elapsed_s,
    }


def _run_mypy() -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "advanced/src", "--strict", "--ignore-missing-imports"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    elapsed_s = round(time.perf_counter() - t0, 2)
    out = (proc.stdout + "\n" + proc.stderr).strip()
    lines = out.splitlines()
    # mypy's own verdict line starts with "Success:" or "Found N error(s)" -- python's
    # sitecustomize.py prints unrelated torch-preload diagnostics to the same stream on
    # every subprocess invocation, so picking the literal last line can grab that instead.
    summary_line = next(
        (ln for ln in reversed(lines) if ln.startswith("Success:") or ln.startswith("Found ")),
        lines[-1] if lines else "",
    )
    return {"raw_summary_line": summary_line, "returncode": proc.returncode, "elapsed_s": elapsed_s, "passed": proc.returncode == 0}


def main() -> None:
    results = {}
    all_ok = True
    for name, subdir, args in SUITES:
        cwd = (ROOT / subdir) if subdir else ROOT
        print(f"[run_tests_snapshot] running {name} ({cwd} :: {' '.join(args)}) ...")
        res = _run_suite(cwd, args)
        results[name] = res
        print(f"  -> {res['raw_summary_line']} (exit {res['returncode']}, {res['elapsed_s']}s)")
        if res["returncode"] not in (0, 5):  # 5 = pytest "no tests collected", not a failure of this script
            all_ok = False

    # mypy status is reported for real, but deliberately does NOT gate this script's exit
    # code or all_passed -- it's a separate, pre-existing check (make mypy) with its own
    # target; failing it here would block `make reproduce` on something out of today's scope.
    print("[run_tests_snapshot] running mypy --strict on advanced/src ...")
    try:
        mypy_res = _run_mypy()
        print(f"  -> {mypy_res['raw_summary_line']} (exit {mypy_res['returncode']}, {mypy_res['elapsed_s']}s)")
    except FileNotFoundError:
        mypy_res = {"raw_summary_line": "mypy not installed", "returncode": None, "elapsed_s": 0, "passed": None}
        print("  -> mypy not installed, skipping")

    snapshot = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "all_passed": all_ok,
        "suites": results,
        "mypy": mypy_res,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE / "test_results.json"
    out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"[run_tests_snapshot] wrote {out_path}")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
