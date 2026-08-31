#!/usr/bin/env python3
"""
Threshold sweep for the semantic layer (advanced/src/harness/semantic.py), run on a
held-out DEV subset of CUAD, disjoint (different seed) from the sample
eval_cuad_ground_truth.py reports as the final number -- picking a threshold using
the same data you report your final result on is exactly the kind of self-grading
CHANGELOG #12 already called out and fixed once elsewhere in this project. Dev/final
split is seeded and disclosed so it's reproducible and auditable.

Each dev contract is embedded exactly once (raw cosine scores cached via
semantic_candidates()); every threshold in --thresholds is then evaluated against
that same cache, so the sweep costs the same real API budget as testing one
threshold, not N.

Usage: python scripts/tune_semantic_threshold.py [--dev-size N] [--seed S]
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

from advanced.src.harness.extract import extract_clauses  # noqa: E402
from advanced.src.harness.ingest import Page  # noqa: E402
from advanced.src.harness.semantic import semantic_candidates  # noqa: E402

RULE_CUAD_MAP: dict[str, list[str]] = {
    "Renewal Term": ["Renewal Term"],
    "Notice Period to Terminate Renewal": ["Notice Period To Terminate Renewal"],
    "Termination for Convenience": ["Termination For Convenience"],
    "Cap on Liability": ["Cap On Liability", "Uncapped Liability"],
    "Limitation of Liability": ["Cap On Liability", "Uncapped Liability"],
    "Audit Rights": ["Audit Rights"],
    "Governing Law": ["Governing Law"],
    "License Grant": ["License Grant"],
    "Non-Compete": ["Non-Compete"],
    "Non-Disparagement": ["Non-Disparagement"],
    "IP Ownership Assignment": ["Ip Ownership Assignment"],
    "Post-Termination Services": ["Post-Termination Services"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-size", type=int, default=40)
    ap.add_argument("--seed", type=int, default=99, help="disjoint from eval_cuad_ground_truth.py's default seed=42")
    ap.add_argument("--thresholds", type=str, default="0.45,0.50,0.55,0.60,0.65,0.70,0.75")
    args = ap.parse_args()

    cuad = json.loads(CUAD_JSON.read_text(encoding="utf-8"))["data"]
    random.Random(args.seed).shuffle(cuad)
    dev = cuad[: args.dev_size]
    (ROOT / "evidence" / "benchmarks").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence" / "benchmarks" / "semantic_dev_set_ids.json").write_text(
        json.dumps(sorted(c["title"] for c in dev), indent=2), encoding="utf-8"
    )

    thresholds = [float(t) for t in args.thresholds.split(",")]

    per_doc = []
    for i, c in enumerate(dev):
        para = c["paragraphs"][0]
        txt = para["context"]
        qas_by_cat = {qa["id"].split("__")[-1]: qa for qa in para["qas"]}
        pages = [Page(num=1, text=txt, start=0, end=len(txt))]
        regex_hits = extract_clauses(txt, pages)
        raw_candidates = semantic_candidates(txt, pages, regex_hits)
        gold = {rule: any(not qas_by_cat[cc]["is_impossible"] for cc in cats if cc in qas_by_cat) for rule, cats in RULE_CUAD_MAP.items()}
        regex_found = {h.clause_type for h in regex_hits}
        per_doc.append({"gold": gold, "regex_found": regex_found, "candidates": raw_candidates})
        print(f"  embedded {i+1}/{len(dev)} ({len(raw_candidates)} candidates)", file=sys.stderr)

    print(f"\n{'Threshold':>10s} {'Recall':>8s} {'Precision':>10s} {'TP':>5s} {'FP':>5s} {'FN':>5s} {'d_recall_vs_regex':>19s}")
    base_tp = base_fn = base_fp = 0
    for rule in RULE_CUAD_MAP:
        for d in per_doc:
            found = rule in d["regex_found"]
            gold = d["gold"][rule]
            if gold and found:
                base_tp += 1
            elif gold and not found:
                base_fn += 1
            elif not gold and found:
                base_fp += 1
    base_recall = base_tp / (base_tp + base_fn) if (base_tp + base_fn) else 0.0
    base_precision = base_tp / (base_tp + base_fp) if (base_tp + base_fp) else 0.0
    print(f"{'regex-only':>10s} {base_recall*100:7.1f}% {base_precision*100:9.1f}% {base_tp:5d} {base_fp:5d} {base_fn:5d} {'--':>19s}")

    for thr in thresholds:
        tp = fp = fn = 0
        for rule in RULE_CUAD_MAP:
            for d in per_doc:
                semantic_found = any(ctype == rule and score >= thr for (_s, _e, _t, ctype, score) in d["candidates"])
                found = rule in d["regex_found"] or semantic_found
                gold = d["gold"][rule]
                if gold and found:
                    tp += 1
                elif gold and not found:
                    fn += 1
                elif not gold and found:
                    fp += 1
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        print(f"{thr:10.2f} {recall*100:7.1f}% {precision*100:9.1f}% {tp:5d} {fp:5d} {fn:5d} {(recall-base_recall)*100:+18.1f}%")


if __name__ == "__main__":
    main()
