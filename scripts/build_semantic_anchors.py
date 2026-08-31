#!/usr/bin/env python3
"""
One-time (re-runnable) build of real embedding anchors for the 11 playbook clause
types, using CUAD's own official category descriptions (docs/research/cuad/
category_descriptions.csv) as the anchor text -- not phrasing we invented, the
actual expert-written definition of each category from the dataset itself.

Writes advanced/src/harness/data/clause_anchors.json: {clause_type: {"texts": [...],
"embeddings": [[...], ...]}}. Committed to the repo so eval/extraction runs don't
need to re-embed the (fixed, small) anchor set every time -- only per-document
candidate sentences are embedded at run time.

Usage: python scripts/build_semantic_anchors.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from advanced.src.harness.embed import embed_available, embed_texts  # noqa: E402

CSV_PATH = ROOT / "docs" / "research" / "cuad" / "category_descriptions.csv"
OUT_PATH = ROOT / "advanced" / "src" / "harness" / "data" / "clause_anchors.json"

# Our 11 playbook types -> exact CUAD category name(s) whose official description we
# use as the anchor. Cap on Liability and Limitation of Liability (advanced's split of
# CUAD's single "Cap on Liability" / "Uncapped Liability" pair) both anchor to the same
# two CUAD descriptions since that's the real, closest-matching pair.
ANCHOR_MAP: dict[str, list[str]] = {
    "Renewal Term": ["Renewal Term"],
    "Notice Period to Terminate Renewal": ["Notice Period to Terminate Renewal"],
    "Termination for Convenience": ["Termination for Convenience"],
    "Cap on Liability": ["Cap on Liability", "Uncapped Liability"],
    "Limitation of Liability": ["Cap on Liability", "Uncapped Liability"],
    "Audit Rights": ["Audit Rights"],
    "Governing Law": ["Governing Law"],
    "License Grant": ["License Grant"],
    "Non-Compete": ["Non-Compete"],
    "Non-Disparagement": ["Non-Disparagement"],
    "IP Ownership Assignment": ["IP Ownership Assignment"],
    "Post-Termination Services": ["Post-Termination Services"],
}


def load_descriptions() -> dict[str, str]:
    out: dict[str, str] = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cat = row["Category (incl. context and answer)"].replace("Category: ", "").strip()
            desc = row["Description"].replace("Description: ", "").strip()
            out[cat] = desc
    return out


def main() -> None:
    if not embed_available():
        print("No embedding provider key available (or EVAL_MOCK=1) -- cannot build real anchors.", file=sys.stderr)
        sys.exit(1)

    descriptions = load_descriptions()
    result: dict[str, dict] = {}
    for clause_type, cuad_cats in ANCHOR_MAP.items():
        texts = [clause_type]  # the clause-type name itself is also a real anchor signal
        for cat in cuad_cats:
            desc = descriptions.get(cat)
            if desc:
                texts.append(f"{cat}: {desc}")
        embeddings = embed_texts(texts)
        if embeddings is None:
            print(f"Embedding failed for {clause_type!r}", file=sys.stderr)
            sys.exit(1)
        result[clause_type] = {"texts": texts, "embeddings": embeddings}
        print(f"  {clause_type}: {len(texts)} anchor texts embedded")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({sum(len(v['texts']) for v in result.values())} total anchor embeddings)")


if __name__ == "__main__":
    main()
