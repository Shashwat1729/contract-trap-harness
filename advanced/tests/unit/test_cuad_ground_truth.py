"""
Regression guard for the primary metric (scripts/eval_cuad_ground_truth.py) -- runs it on a
small random sample of the real CUAD dataset (not the full 510, to keep the test suite fast)
and asserts the basic, load-bearing claim: advanced meaningfully beats baseline on real,
independent expert-labeled ground truth, at reasonable precision. This does not assert exact
percentages (those can shift a little as CLAUSE_PATTERNS evolves) -- it guards against a
regression silently reversing the whole point of CHANGELOG #12.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
CUAD_JSON = ROOT / "docs" / "research" / "cuad" / "CUADv1.json"

pytestmark = pytest.mark.skipif(not CUAD_JSON.exists(), reason="docs/research/cuad/CUADv1.json not present in this checkout")


def test_cuad_ground_truth_sanity(tmp_path) -> None:
    # --out points at a throwaway file so this never overwrites the canonical, full-510-contract
    # evidence/benchmarks/cuad_ground_truth_results.json the dashboard actually reads.
    out = tmp_path / "cuad_ground_truth_sample.json"
    subprocess.run(
        [sys.executable, "scripts/eval_cuad_ground_truth.py", "--sample", "80", "--seed", "7", "--out", str(out)],
        cwd=str(ROOT), check=True, capture_output=True, text=True, timeout=60,
    )
    result = json.loads(out.read_text(encoding="utf-8"))
    adv = result["advanced"]["overall"]
    base = result["baseline"]["overall"]

    assert adv["recall"] is not None and base["recall"] is not None
    assert adv["recall"] > base["recall"], "advanced should meaningfully beat baseline on real CUAD ground truth"
    assert adv["recall"] > 0.25, f"advanced recall regressed badly: {adv['recall']}"
    assert adv["precision"] is not None and adv["precision"] > 0.7, f"advanced precision regressed badly: {adv['precision']}"
