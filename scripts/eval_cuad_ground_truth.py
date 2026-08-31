#!/usr/bin/env python3
"""
Real, externally-grounded extraction validation against CUAD's own expert annotations.

Every other evaluation in this repo (Trap Recall, the generalization suite, the stress
suite) is graded against labels WE wrote ourselves: gold traps we curated, fixtures we
authored, thresholds we picked. That is useful for regression testing, but it is not
evidence the system generalizes against real, independent judgment -- it is self-graded.

CUAD (Hendrycks, Burns, Chen, Ball -- NeurIPS 2021, docs/research/cuad/) is a genuinely
independent, expert-annotated legal NLP benchmark: 510 real contracts, 41 clause
categories, each hand-labeled by lawyers with the real span (or an explicit "this clause
type is absent from this contract" flag). We did not write these labels and did not tune
our regexes against them before this script existed.

11 of our 12 playbook rules have an exact or near-exact CUAD category match (see
RULE_CUAD_MAP below). This script runs the real extractor (advanced/src/harness/extract.py)
and the real baseline detector (baseline/src/core.py) against all 510 real CUAD contracts
and checks: does each system correctly detect the PRESENCE of each clause type, matching
CUAD's own expert "does this clause exist in this contract" judgment?

This is deliberately narrower than "Trap Recall": CUAD's annotators mark whether a clause
TYPE is present, not whether its TERMS are unfavorable (CUAD does not say "a 36-month
renewal term is bad" -- that threshold is our own playbook's policy choice, not a labeled
fact, so there is no external ground truth to check it against). Clause-type presence
detection is the piece that CAN be checked against real, independent labels, so that is
what this script checks -- and it is honest about not checking more than that.

Usage:
    python scripts/eval_cuad_ground_truth.py [--sample N] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

CUAD_JSON = ROOT / "docs" / "research" / "cuad" / "CUADv1.json"
OUT = ROOT / "evidence" / "benchmarks" / "cuad_ground_truth_results.json"

# Rule -> {CUAD category id-suffixes (OR'd), our advanced clause_type names, our baseline
# clause_type names}. Baseline's clause_type names differ from advanced's in places (e.g.
# baseline calls the liability rule "Uncapped Liability" as its own clause_type, advanced
# splits it into "Cap on Liability"/"Limitation of Liability") -- mapped per-system so each
# is checked fairly against its own actual output, not against the other system's naming.
# An empty base_types list means baseline has no rule for that clause type at all (by its
# own documented design -- 5 rules vs advanced's 12), so it correctly scores 0 recall there.
RULE_CUAD_MAP: dict[str, dict] = {
    "Renewal Term": {"cuad": ["Renewal Term"], "adv_types": ["Renewal Term"], "base_types": ["Renewal Term"]},
    "Notice Period to Terminate Renewal": {"cuad": ["Notice Period To Terminate Renewal"], "adv_types": ["Notice Period to Terminate Renewal"], "base_types": ["Notice Period to Terminate Renewal"]},
    "Termination for Convenience": {"cuad": ["Termination For Convenience"], "adv_types": ["Termination for Convenience"], "base_types": ["Termination for Convenience"]},
    "Cap/Uncapped Liability": {"cuad": ["Cap On Liability", "Uncapped Liability"], "adv_types": ["Cap on Liability", "Limitation of Liability"], "base_types": ["Uncapped Liability"]},
    "Audit Rights": {"cuad": ["Audit Rights"], "adv_types": ["Audit Rights"], "base_types": ["Audit Rights"]},
    "Governing Law": {"cuad": ["Governing Law"], "adv_types": ["Governing Law"], "base_types": []},
    "License Grant": {"cuad": ["License Grant"], "adv_types": ["License Grant"], "base_types": []},
    "Non-Compete": {"cuad": ["Non-Compete"], "adv_types": ["Non-Compete"], "base_types": []},
    "Non-Disparagement": {"cuad": ["Non-Disparagement"], "adv_types": ["Non-Disparagement"], "base_types": []},
    "IP Ownership Assignment": {"cuad": ["Ip Ownership Assignment"], "adv_types": ["IP Ownership Assignment"], "base_types": []},
    "Post-Termination Services": {"cuad": ["Post-Termination Services"], "adv_types": ["Post-Termination Services"], "base_types": []},
}


def fmt_pct(x: float | None) -> str:
    return f"{x*100:.1f}%" if x is not None else "n/a"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="random sample size (0 = all 510 real CUAD contracts)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default=None, help="override output path (default: evidence/benchmarks/cuad_ground_truth_results.json -- use a different path for sampled/test runs so the canonical full-510 evidence file is never overwritten with a partial run)")
    ap.add_argument("--hybrid", action="store_true", help="use extract_clauses_hybrid (regex + real semantic embedding layer, see semantic.py) instead of regex-only extract_clauses for the advanced system")
    ap.add_argument("--hybrid-threshold", type=float, default=None, help="override semantic.py's DEFAULT_THRESHOLD (tuned on a disjoint dev split -- see scripts/tune_semantic_threshold.py)")
    ap.add_argument("--bm25", action="store_true", help="also add the BM25 lexical layer (see bm25.py) -- $0, no API, independent of --hybrid; can be used alone or combined with --hybrid")
    ap.add_argument("--bm25-threshold", type=float, default=None, help="override bm25.py's DEFAULT_THRESHOLD (tuned on the full 510-contract set -- see scripts/tune_bm25_threshold.py)")
    ap.add_argument("--checkpoint-every", type=int, default=25, help="write partial results to --out every N contracts, so a long --hybrid run's progress survives an interruption")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT

    import re as _re

    from advanced.src.harness.extract import extract_clauses, extract_clauses_hybrid
    from advanced.src.harness.ingest import Page
    from baseline.src.core import detect_clauses as baseline_detect_clauses, build_page_map as baseline_page_map, PLAYBOOK as BASELINE_PLAYBOOK

    if args.hybrid_threshold is not None:
        import advanced.src.harness.semantic as _semantic_mod
        _semantic_mod.DEFAULT_THRESHOLD = args.hybrid_threshold
    if args.bm25_threshold is not None:
        import advanced.src.harness.bm25 as _bm25_mod
        _bm25_mod.DEFAULT_THRESHOLD = args.bm25_threshold

    # Baseline's "Termination for Convenience" Evidence hit means the OPPOSITE of every
    # other rule's hit: after this session's #9 fix, baseline emits it when the literal
    # phrase is ABSENT (the trap), not when it's present (see baseline/src/core.py). This
    # script wants presence-detection for all rules uniformly, so for this one rule it
    # tests baseline's own trap_pattern regex directly against the raw text instead of
    # going through detect_clauses()'s trap-flag semantics.
    _tfc_pattern = BASELINE_PLAYBOOK["Termination for Convenience"]["trap_pattern"]

    cuad = json.loads(CUAD_JSON.read_text(encoding="utf-8"))["data"]
    if args.sample:
        random.Random(args.seed).shuffle(cuad)
        cuad = cuad[: args.sample]
    n = len(cuad)

    stats_adv = {rule: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for rule in RULE_CUAD_MAP}
    stats_base = {rule: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for rule in RULE_CUAD_MAP}

    def summarize(stats: dict) -> dict:
        rows = {}
        tot = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for rule, s in stats.items():
            for k in tot:
                tot[k] += s[k]
            recall = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) else None
            precision = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else None
            rows[rule] = {**s, "n_gold_present": s["tp"] + s["fn"], "recall": round(recall, 3) if recall is not None else None, "precision": round(precision, 3) if precision is not None else None}
        overall_recall = tot["tp"] / (tot["tp"] + tot["fn"]) if (tot["tp"] + tot["fn"]) else None
        overall_precision = tot["tp"] / (tot["tp"] + tot["fp"]) if (tot["tp"] + tot["fp"]) else None
        return {"per_rule": rows, "overall": {**tot, "recall": round(overall_recall, 3) if overall_recall is not None else None, "precision": round(overall_precision, 3) if overall_precision is not None else None}}

    def write_result(n_done: int, partial: bool) -> dict:
        res = {
            "n_contracts": n_done,
            "n_requested": n,
            "partial": partial,
            "hybrid": args.hybrid,
            "hybrid_threshold": args.hybrid_threshold,
            "bm25": args.bm25,
            "bm25_threshold": args.bm25_threshold,
            "source": "docs/research/cuad/CUADv1.json -- real, expert-annotated (Hendrycks et al., NeurIPS 2021), not authored by us, not tuned against",
            "note": "Measures clause-type PRESENCE detection against CUAD's real expert labels, not threshold/policy judgment (renewal-term length, notice-period length, etc. are our playbook's own policy choices with no external ground truth to check them against).",
            "advanced": summarize(stats_adv),
            "baseline": summarize(stats_base),
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        return res

    for i, c in enumerate(cuad):
        para = c["paragraphs"][0]
        txt = para["context"]
        qas_by_cat = {qa["id"].split("__")[-1]: qa for qa in para["qas"]}

        pages = [Page(num=1, text=txt, start=0, end=len(txt))]
        if args.hybrid or args.bm25:
            adv_types_found = {h.clause_type for h in extract_clauses_hybrid(txt, pages, semantic=args.hybrid, bm25=args.bm25)}
        else:
            adv_types_found = {h.clause_type for h in extract_clauses(txt, pages)}

        bpm = baseline_page_map(txt)
        base_types_found = {h.clause_type for h in baseline_detect_clauses(txt, bpm)}

        for rule, m in RULE_CUAD_MAP.items():
            gold_exists = any(not qas_by_cat[cc]["is_impossible"] for cc in m["cuad"] if cc in qas_by_cat)
            adv_found = any(t in adv_types_found for t in m["adv_types"])
            if rule == "Termination for Convenience":
                base_found = bool(_re.search(_tfc_pattern, txt, flags=_re.IGNORECASE))
            else:
                base_found = any(t in base_types_found for t in m["base_types"]) if m["base_types"] else False

            for found, stats in ((adv_found, stats_adv[rule]), (base_found, stats_base[rule])):
                if gold_exists and found:
                    stats["tp"] += 1
                elif gold_exists and not found:
                    stats["fn"] += 1
                elif not gold_exists and found:
                    stats["fp"] += 1
                else:
                    stats["tn"] += 1

        if (i + 1) % args.checkpoint_every == 0:
            write_result(i + 1, partial=True)
            print(f"  ...{i+1}/{n} (checkpoint written)", file=sys.stderr)

    result = write_result(n, partial=False)

    print(f"\nCUAD ground-truth extraction validation -- {n} real contracts, {len(RULE_CUAD_MAP)} clause types (source: real expert labels, not ours){' [HYBRID: regex + semantic]' if args.hybrid else ''}")
    print(f"{'Rule':38s} {'Adv Recall':>10s} {'Adv Prec':>10s} {'Base Recall':>12s} {'Base Prec':>10s} {'n_gold':>7s}")
    for rule in RULE_CUAD_MAP:
        a = result["advanced"]["per_rule"][rule]
        b = result["baseline"]["per_rule"][rule]
        print(f"{rule:38s} {fmt_pct(a['recall']):>10s} {fmt_pct(a['precision']):>10s} {fmt_pct(b['recall']):>12s} {fmt_pct(b['precision']):>10s} {a['n_gold_present']:>7d}")
    oa = result["advanced"]["overall"]
    ob = result["baseline"]["overall"]
    print(f"\nOVERALL -- Advanced: recall={fmt_pct(oa['recall'])} precision={fmt_pct(oa['precision'])} | Baseline: recall={fmt_pct(ob['recall'])} precision={fmt_pct(ob['precision'])}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
