#!/usr/bin/env python3
"""
Real, independent-METHOD comparison point: a zero-shot LLM (gemini-2.5-flash via
litellm, same LLM_MODEL this repo already uses for llm_verify.py/llm_judge.py) asked
directly whether each of the 11 playbook clause types is present in a real CUAD
contract, scored against CUAD's own expert labels with the exact same TP/FP/FN/TN
methodology as scripts/eval_cuad_ground_truth.py.

Why this exists: the previous CUAD ground-truth pass (CHANGELOG #12) validated our
own regex extractor against real external labels, which is real progress -- but every
number on that scoreboard was still produced by code we wrote. This script adds a
third column that is neither ours: what does a frontier LLM, asked cold with no
prompt-tuning against CUAD, get on the identical contracts and identical metric? This
is the closest fair reference point to published zero-shot legal-LLM benchmarks (e.g.
ContractEval, arxiv 2508.03080, GPT-4.1 F1=0.641 on CUAD span extraction -- a stricter
span-match metric than presence detection, so not directly equal, but the right
neighborhood to sanity-check against).

One LLM call per contract (all 11 rules asked together in one prompt), not 11 calls
per contract -- keeps this feasible under a free-tier daily request cap. Sample size
is intentionally modest and disclosed; this is a real, live, partial run in the same
spirit as evidence/benchmarks/llm_judge_results.json's disclosed partial sample, not
a full-510 claim.

Usage:
    python scripts/eval_llm_zeroshot_baseline.py [--sample N] [--seed S] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

CUAD_JSON = ROOT / "docs" / "research" / "cuad" / "CUADv1.json"
OUT = ROOT / "evidence" / "benchmarks" / "llm_zeroshot_baseline_results.json"

from advanced.src.harness.llm import call_llm_json, llm_available, LLM_MODEL  # noqa: E402

RULE_CUAD_MAP: dict[str, list[str]] = {
    "Renewal Term": ["Renewal Term"],
    "Notice Period to Terminate Renewal": ["Notice Period To Terminate Renewal"],
    "Termination for Convenience": ["Termination For Convenience"],
    "Cap/Uncapped Liability": ["Cap On Liability", "Uncapped Liability"],
    "Audit Rights": ["Audit Rights"],
    "Governing Law": ["Governing Law"],
    "License Grant": ["License Grant"],
    "Non-Compete": ["Non-Compete"],
    "Non-Disparagement": ["Non-Disparagement"],
    "IP Ownership Assignment": ["Ip Ownership Assignment"],
    "Post-Termination Services": ["Post-Termination Services"],
}

SYSTEM_PROMPT = (
    "You are a contract review assistant. You will be given the full text of one real "
    "commercial contract. For each of the 11 named clause types below, answer whether "
    "that clause type is genuinely present anywhere in this contract. Judge strictly: "
    "answer true only if the specific clause type is actually there, not merely a "
    "loosely related topic. Reply with ONLY a single JSON object, no prose, no markdown "
    "fence, exactly this shape (all 11 keys required, boolean values only):\n"
    '{"Renewal Term": bool, "Notice Period to Terminate Renewal": bool, '
    '"Termination for Convenience": bool, "Cap/Uncapped Liability": bool, '
    '"Audit Rights": bool, "Governing Law": bool, "License Grant": bool, '
    '"Non-Compete": bool, "Non-Disparagement": bool, "IP Ownership Assignment": bool, '
    '"Post-Termination Services": bool}'
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42, help="same seed/shuffle as eval_cuad_ground_truth.py's default full run, so this sample is a real subset of that same population")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--max-chars", type=int, default=12000, help="truncate contract text to this length before sending to the LLM (context budget)")
    ap.add_argument("--pace-s", type=float, default=13.0, help="seconds to sleep before each call after the first -- the free-tier per-minute cap (quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier, quotaValue 5) is scoped per PROJECT, so rotating across this repo's 5 keys does not multiply effective throughput when they share a project; pacing under 5/min avoids burning the whole pool in seconds")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT

    if not llm_available():
        print("No LLM key available (or EVAL_MOCK=1) -- cannot run a real zero-shot baseline.", file=sys.stderr)
        sys.exit(1)

    cuad = json.loads(CUAD_JSON.read_text(encoding="utf-8"))["data"]
    random.Random(args.seed).shuffle(cuad)
    sample = cuad[: args.sample]

    stats = {rule: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for rule in RULE_CUAD_MAP}
    per_contract = []
    n_ran = 0
    for i, c in enumerate(sample):
        if i > 0 and args.pace_s > 0:
            time.sleep(args.pace_s)
        para = c["paragraphs"][0]
        txt = para["context"]
        qas_by_cat = {qa["id"].split("__")[-1]: qa for qa in para["qas"]}
        gold = {rule: any(not qas_by_cat[cc]["is_impossible"] for cc in cats if cc in qas_by_cat) for rule, cats in RULE_CUAD_MAP.items()}

        mock = {rule: False for rule in RULE_CUAD_MAP}
        t0 = time.perf_counter()
        result = call_llm_json(
            SYSTEM_PROMPT,
            f"Contract text:\n\"\"\"\n{txt[:args.max_chars]}\n\"\"\"\n\nReturn the JSON object.",
            # Generous max_tokens: Gemini 2.5 "thinking" models spend part of the output
            # budget on hidden reasoning before the visible JSON reply (see llm_verify.py's
            # identical comment) -- 500 was too tight and truncated nearly every real call
            # before a single closing brace, discovered only once pacing (--pace-s) let calls
            # actually reach the model instead of being blocked by quota exhaustion.
            max_tokens=1000,
            mock_response=mock,
        )
        ran = bool(result.get("_ran", False))
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        if not ran:
            print(f"  [{i+1}/{len(sample)}] {c['title'][:50]!r}: LLM call failed/mocked ({result.get('_error', 'no key?')}) -- skipping from scored set", file=sys.stderr)
            per_contract.append({"title": c["title"], "ran": False, "error": result.get("_error")})
            continue
        n_ran += 1
        predicted = {rule: bool(result.get(rule, False)) for rule in RULE_CUAD_MAP}
        for rule in RULE_CUAD_MAP:
            g, p = gold[rule], predicted[rule]
            if g and p:
                stats[rule]["tp"] += 1
            elif g and not p:
                stats[rule]["fn"] += 1
            elif not g and p:
                stats[rule]["fp"] += 1
            else:
                stats[rule]["tn"] += 1
        per_contract.append({"title": c["title"], "ran": True, "gold": gold, "predicted": predicted, "latency_ms": elapsed_ms})
        print(f"  [{i+1}/{len(sample)}] {c['title'][:50]!r}: ok ({elapsed_ms}ms)", file=sys.stderr)

    tot = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    rows = {}
    for rule, s in stats.items():
        for k in tot:
            tot[k] += s[k]
        recall = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) else None
        precision = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else None
        rows[rule] = {**s, "recall": round(recall, 3) if recall is not None else None, "precision": round(precision, 3) if precision is not None else None}
    overall_recall = tot["tp"] / (tot["tp"] + tot["fn"]) if (tot["tp"] + tot["fn"]) else None
    overall_precision = tot["tp"] / (tot["tp"] + tot["fp"]) if (tot["tp"] + tot["fp"]) else None

    result = {
        "model": LLM_MODEL,
        "source": "docs/research/cuad/CUADv1.json -- real, expert-annotated (Hendrycks et al., NeurIPS 2021)",
        "note": "Real, live zero-shot LLM calls, one per contract (all 11 rules asked together). n_requested is the sample size requested; n_scored is how many actually returned a real (non-mock, non-error) response and were scored -- if these differ, some contracts hit a rate limit or transient error and were excluded from the scored stats rather than silently counted as failures either direction.",
        "n_requested": len(sample),
        "n_scored": n_ran,
        "per_rule": rows,
        "overall": {**tot, "recall": round(overall_recall, 3) if overall_recall is not None else None, "precision": round(overall_precision, 3) if overall_precision is not None else None},
        "per_contract": per_contract,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nLLM zero-shot baseline ({LLM_MODEL}) -- {n_ran}/{len(sample)} contracts scored (rest failed/rate-limited)")
    print(f"{'Rule':38s} {'Recall':>8s} {'Precision':>10s} {'n_gold':>7s}")
    for rule, r in rows.items():
        rec = f"{r['recall']*100:.1f}%" if r["recall"] is not None else "n/a"
        prec = f"{r['precision']*100:.1f}%" if r["precision"] is not None else "n/a"
        print(f"{rule:38s} {rec:>8s} {prec:>10s} {r['tp']+r['fn']:7d}")
    orv = f"{overall_recall*100:.1f}%" if overall_recall is not None else "n/a"
    opv = f"{overall_precision*100:.1f}%" if overall_precision is not None else "n/a"
    print(f"\nOVERALL -- recall={orv} precision={opv}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
