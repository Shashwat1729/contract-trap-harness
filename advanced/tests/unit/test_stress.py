"""
Codifies the stress suite (shared/fixtures/stress/) as a real pytest test, same reasoning
as test_generalization.py -- a regression here fails CI directly instead of only showing up
if someone remembers to run scripts/eval_stress.py by hand.

See CHANGELOG.md for why this suite exists: the generalization suite proved the 12 rules
work individually on fresh, clean, well-formatted prose. This suite pushes into messier
real-world territory -- OCR-style whitespace noise, ALL CAPS/em-dash headers, long documents
with decoy numbers, multi-level subsection numbering, non-US drafting conventions, and common
real-world phrasing no existing regex happened to cover -- and is what actually found three
real bugs (fixed, not the fixtures tuned around them).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "shared" / "fixtures" / "stress"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def _run(cid: str) -> dict:
    from advanced.src.harness.ingest import Page
    from advanced.src.core import process_contract_advanced

    txt = (FIXTURES / f"{cid}.txt").read_text(encoding="utf-8")
    pages = [Page(num=1, text=txt, start=0, end=len(txt))]
    return process_contract_advanced(txt, pages, contract_id=cid, turn=1)


@pytest.mark.parametrize("case", [m for m in MANIFEST if not m.get("known_gap")], ids=lambda m: m["id"])
def test_stress_case(case: dict) -> None:
    result = _run(case["id"])
    approved_rules = {f["rule_id"] for f in result.get("approved_candidates", [])}
    coverage_gap_rules = {g["rule_id"] for g in result.get("coverage_gaps", [])}

    expected = case["trap_expected"]
    rule_id = case.get("rule_id")
    if expected == "coverage_gap":
        assert rule_id in coverage_gap_rules, f"{case['id']}: expected {rule_id} as a coverage gap, got {coverage_gap_rules}"
    elif expected is True:
        assert rule_id in approved_rules, f"{case['id']}: expected {rule_id} to be approved, got {approved_rules}"
    else:
        assert not approved_rules, f"{case['id']} (clean contract): expected no findings, got {approved_rules}"
