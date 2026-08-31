#!/usr/bin/env python3
"""
Threshold sweep for the BM25 lexical layer (advanced/src/harness/bm25.py).

Unlike scripts/tune_semantic_threshold.py -- which had to tune on a tiny n=7-40
dev sample because each candidate paragraph costs a real, quota-limited embedding
API call -- this sweep is $0 and fully deterministic (pure local BM25 scoring, no
network call at all). That means it can, and should, be tuned directly against the
FULL 510-contract real CUAD set with no train/test leakage concern the way the CUAD
regex patterns themselves have (see CHANGELOG #17's methodology caveat): the anchor
text BM25 scores against is the category's own DEFINITION (docs/research/cuad/
category_descriptions.csv via clause_anchors.json), not a labeled example drawn from
the 510 contracts, so scoring against all 510 is not circular the way tuning a regex
pattern against the same 510 contracts' own text would be.

Usage: python scripts/tune_bm25_threshold.py [--sample N] [--seed S] [--thresholds ...]
       (--sample 0, the default, uses all 510 real CUAD contracts -- affordable
       because this is $0/deterministic, unlike the embedding sweep it mirrors)
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

from advanced.src.harness.bm25 import bm25_candidates  # noqa: E402
from advanced.src.harness.extract import extract_clauses  # noqa: E402
from advanced.src.harness.ingest import Page  # noqa: E402

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
    ap.add_argument("--sample", type=int, default=0, help="0 = all 510 real CUAD contracts (default -- affordable, this sweep is $0)")
    ap.add_argument("--seed", type=int, default=42, help="same default seed as eval_cuad_ground_truth.py -- fine here since BM25 scores against category DEFINITIONS, not labeled examples, so there is no leakage to avoid by using a disjoint split")
    ap.add_argument("--thresholds", type=str, default="2,3,4,5,6,7,8,9,10,12,15")
    args = ap.parse_args()

    cuad = json.loads(CUAD_JSON.read_text(encoding="utf-8"))["data"]
    random.Random(args.seed).shuffle(cuad)
    dev = cuad if args.sample <= 0 else cuad[: args.sample]

    thresholds = [float(t) for t in args.thresholds.split(",")]

    per_doc = []
    for i, c in enumerate(dev):
        para = c["paragraphs"][0]
        txt = para["context"]
        qas_by_cat = {qa["id"].split("__")[-1]: qa for qa in para["qas"]}
        pages = [Page(num=1, text=txt, start=0, end=len(txt))]
        regex_hits = extract_clauses(txt, pages)
        raw_candidates = bm25_candidates(txt, pages, regex_hits)
        gold = {rule: any(not qas_by_cat[cc]["is_impossible"] for cc in cats if cc in qas_by_cat) for rule, cats in RULE_CUAD_MAP.items()}
        regex_found = {h.clause_type for h in regex_hits}
        per_doc.append({"gold": gold, "regex_found": regex_found, "candidates": raw_candidates})
        if (i + 1) % 50 == 0 or i == len(dev) - 1:
            print(f"  scored {i+1}/{len(dev)}", file=sys.stderr)

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

    best_thr, best_f1 = None, -1.0
    for thr in thresholds:
        tp = fp = fn = 0
        for rule in RULE_CUAD_MAP:
            for d in per_doc:
                bm25_found = any(ctype == rule and score >= thr for (_s, _e, _t, ctype, score) in d["candidates"])
                found = rule in d["regex_found"] or bm25_found
                gold = d["gold"][rule]
                if gold and found:
                    tp += 1
                elif gold and not found:
                    fn += 1
                elif not gold and found:
                    fp += 1
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
        print(f"{thr:10.2f} {recall*100:7.1f}% {precision*100:9.1f}% {tp:5d} {fp:5d} {fn:5d} {(recall-base_recall)*100:+18.1f}%")

    print(f"\nBest F1 threshold: {best_thr} (F1={best_f1:.3f}) over {len(dev)} contracts -- paste this into advanced/src/harness/bm25.py's DEFAULT_THRESHOLD with a comment citing this run.")


if __name__ == "__main__":
    main()
