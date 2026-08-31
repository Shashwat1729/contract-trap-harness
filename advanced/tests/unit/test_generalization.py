"""
Codifies the held-out generalization suite (shared/fixtures/generalization/) as a real
pytest test, not just a standalone script -- so a regression in any of the 12 playbook
rules, or a new false positive on the clean controls, fails CI/`pytest` directly instead
of only showing up if someone remembers to run scripts/eval_generalization.py by hand.

See CHANGELOG.md #7 for why this suite exists: the original 30-fixture trap suite only
ever exercises 4-5 of the 12 playbook rules and risks test-leakage from hand-authored
trap-injection text. These 14 scored fixtures were written independently of the playbook
text specifically to check generalization, not fit to it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "shared" / "fixtures" / "generalization"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def _run(cid: str) -> dict:
    from advanced.src.harness.ingest import Page
    from advanced.src.core import process_contract_advanced

    txt = (FIXTURES / f"{cid}.txt").read_text(encoding="utf-8")
    pages = [Page(num=1, text=txt, start=0, end=len(txt))]
    return process_contract_advanced(txt, pages, contract_id=cid, turn=1)


@pytest.mark.parametrize("case", [m for m in MANIFEST if not m.get("known_gap")], ids=lambda m: m["id"])
def test_generalization_case(case: dict) -> None:
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


def test_known_gap_is_still_known() -> None:
    """
    gen_15 is a deliberately adversarial, disclosed, unfixed case -- liability described
    as having "no maximum amount" without the literal words "unlimited"/"uncapped". This
    test doesn't assert it fails (that would be testing a bug on purpose); it just makes
    sure the case still runs without crashing, and flags loudly if it starts passing so
    the manifest/CHANGELOG claim can be updated rather than silently going stale.
    """
    gap = next(m for m in MANIFEST if m.get("known_gap"))
    result = _run(gap["id"])
    approved_rules = {f["rule_id"] for f in result.get("approved_candidates", [])}
    caught = gap["rule_id"] in approved_rules
    if caught:
        pytest.fail(
            f"{gap['id']} is now caught (rule {gap['rule_id']} approved) -- this was a documented "
            "known gap; update shared/fixtures/generalization/manifest.json (drop known_gap) and "
            "CHANGELOG.md #7 to reflect the fix instead of leaving this stale."
        )
