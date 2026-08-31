#!/usr/bin/env python3
"""
Held-out generalization suite -- 15 contracts NOT used to tune the playbook/regex logic,
written independently with fresh phrasing (not copied from advanced/src/harness/risk.py's
PLAYBOOK text or from scripts/build_trap_suite.py's injection templates).

Why this exists: the original 30-fixture trap suite (shared/fixtures/contracts/) only ever
exercises 4 of the 12 playbook rules (see evidence/benchmarks/comparison.md's rule-coverage
disclosure) and 18/30 of its fixtures contain hand-authored "ADDENDUM TRAP INJECTION" text
whose vocabulary closely echoes the detection regexes -- a real test-leakage risk. This suite
is the honest generalization check: does detection logic built against those 30 fixtures
still work on contracts it has never seen, covering all 12 rules, including deliberately
different section headers, phrasing, and one adversarial case expected to be MISSED.

Usage:
    python scripts/eval_generalization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "shared" / "fixtures" / "generalization"
OUT = ROOT / "evidence" / "benchmarks" / "generalization_results.json"


def main() -> None:
    from advanced.src.harness.ingest import Page
    from advanced.src.core import process_contract_advanced

    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for m in manifest:
        cid = m["id"]
        txt = (FIXTURES / f"{cid}.txt").read_text(encoding="utf-8")
        pages = [Page(num=1, text=txt, start=0, end=len(txt))]
        result = process_contract_advanced(txt, pages, contract_id=cid, turn=1)
        approved_rules = {f["rule_id"] for f in result.get("approved_candidates", [])}
        all_rules = {f["rule_id"] for f in result.get("findings", [])}
        coverage_gap_rules = {g["rule_id"] for g in result.get("coverage_gaps", [])}

        expected = m["trap_expected"]
        rule_id = m.get("rule_id")
        if expected == "coverage_gap":
            caught = rule_id in coverage_gap_rules
        elif expected is True:
            caught = rule_id in approved_rules
        else:  # expected is False -- clean contract, success = NO findings at all
            caught = len(approved_rules) == 0

        rows.append({
            "id": cid,
            "rule_id": rule_id,
            "name": m["name"],
            "expected": expected,
            "known_gap": m.get("known_gap", False),
            "caught": caught,
            "approved_rules_found": sorted(approved_rules),
            "all_proposed_rules": sorted(all_rules),
            "coverage_gap_rules_found": sorted(coverage_gap_rules),
        })

    non_gap_rows = [r for r in rows if not r["known_gap"]]
    n_pass = sum(1 for r in non_gap_rows if r["caught"])
    known_gap_rows = [r for r in rows if r["known_gap"]]

    summary = {
        "n_cases": len(rows),
        "n_scored": len(non_gap_rows),
        "n_pass": n_pass,
        "pass_rate": round(n_pass / len(non_gap_rows), 3) if non_gap_rows else 0,
        "known_gaps_excluded_from_score": [
            {"id": r["id"], "rule_id": r["rule_id"], "name": r["name"], "caught_anyway": r["caught"]}
            for r in known_gap_rows
        ],
        "failures": [r for r in non_gap_rows if not r["caught"]],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Generalization suite: {n_pass}/{len(non_gap_rows)} scored cases passed ({summary['pass_rate']:.0%})")
    for r in non_gap_rows:
        status = "PASS" if r["caught"] else "FAIL"
        print(f"  [{status}] {r['id']} ({r['rule_id'] or 'clean'}): {r['name']}")
    for r in known_gap_rows:
        print(f"  [KNOWN GAP, not scored] {r['id']} ({r['rule_id']}): caught_anyway={r['caught']}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
