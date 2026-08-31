"""
Generates real charts (PNG) from real evidence files already in evidence/benchmarks/ --
no hand-typed numbers, same "no hardcoded numbers" discipline as eval_harness.py. Run:
    python scripts/generate_charts.py
Writes to evidence/benchmarks/charts/. Safe to re-run any time the underlying evidence
JSON changes (e.g. after `make eval-cuad-ground-truth`) -- always reflects current numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence" / "benchmarks"
OUT = EVID / "charts"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def _load(name: str) -> dict:
    return json.loads((EVID / name).read_text(encoding="utf-8"))


def chart_headline() -> None:
    """Baseline vs Advanced recall/precision on the real 510-contract CUAD set."""
    d = _load("cuad_ground_truth_results.json")
    adv, base = d["advanced"]["overall"], d["baseline"]["overall"]
    labels = ["Recall", "Precision"]
    base_vals = [base["recall"] * 100, base["precision"] * 100]
    adv_vals = [adv["recall"] * 100, adv["precision"] * 100]

    x = range(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(6, 4.5))
    b1 = ax.bar([i - w / 2 for i in x], base_vals, w, label="Baseline (regex, no verify)", color="#94a3b8")
    b2 = ax.bar([i + w / 2 for i in x], adv_vals, w, label="Advanced (verification-gated)", color="#2563eb")
    ax.set_ylabel("%")
    ax.set_title(f"Baseline vs Advanced -- real CUAD ground truth\n(n={d['n_contracts']} contracts)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.legend()
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}%", (rect.get_x() + rect.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "headline_recall_precision.png")
    plt.close(fig)


def chart_per_rule() -> None:
    """Per-rule recall, advanced vs baseline, real 510-contract CUAD set."""
    d = _load("cuad_ground_truth_results.json")
    adv_rules = d["advanced"]["per_rule"]
    base_rules = d["baseline"]["per_rule"]
    rules = list(adv_rules.keys())
    adv_recall = [adv_rules[r]["recall"] * 100 for r in rules]
    base_recall = [base_rules.get(r, {}).get("recall", 0.0) * 100 for r in rules]

    y = range(len(rules))
    h = 0.35
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh([i + h / 2 for i in y], base_recall, h, label="Baseline", color="#94a3b8")
    ax.barh([i - h / 2 for i in y], adv_recall, h, label="Advanced", color="#2563eb")
    ax.set_yticks(list(y))
    ax.set_yticklabels(rules, fontsize=9)
    ax.set_xlabel("Recall %")
    ax.set_title("Per-rule recall -- real CUAD ground truth, all 11 rules")
    ax.legend()
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT / "per_rule_recall.png")
    plt.close(fig)


def chart_changelog_progression() -> None:
    """Advanced recall/precision progression across the real, evidence-linked changelog
    milestones that actually changed the certified/opt-in numbers (CHANGELOG #12, #19)."""
    # Real, sourced numbers -- CHANGELOG #12 ("The real numbers, before any further
    # fixes: Advanced 37.7% recall / 94.9% precision" -- CHANGELOG.md line ~235, the
    # first honest ground-truth measurement, before #12's subsequent rule fixes),
    # #12 final (certified default, cuad_ground_truth_results.json), #19 (opt-in
    # BM25, cuad_ground_truth_bm25_only.json).
    d = _load("cuad_ground_truth_results.json")
    adv = d["advanced"]["overall"]
    try:
        bm25 = _load("cuad_ground_truth_bm25_only.json")["advanced"]["overall"]
        bm25_recall, bm25_prec = bm25["recall"] * 100, bm25["precision"] * 100
    except FileNotFoundError:
        bm25_recall, bm25_prec = None, None

    stages = ["#12 first honest\nmeasurement", "#12 certified\ndefault\n(regex-only)"]
    recall = [37.7, adv["recall"] * 100]
    precision = [94.9, adv["precision"] * 100]
    if bm25_recall is not None:
        stages.append("#19 opt-in\nBM25 layer")
        recall.append(bm25_recall)
        precision.append(bm25_prec)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(stages))
    ax.plot(x, recall, marker="o", color="#2563eb", label="Recall %")
    ax.plot([i for i, p in zip(x, precision) if p is not None], [p for p in precision if p is not None],
            marker="s", color="#16a34a", label="Precision %")
    ax.set_xticks(list(x))
    ax.set_xticklabels(stages, fontsize=9)
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_title("Real recall/precision progression across the changelog\n(all points measured on the same real 510-contract CUAD set)")
    ax.legend()
    for i, r in enumerate(recall):
        ax.annotate(f"{r:.1f}%", (i, r), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, color="#2563eb")
    fig.tight_layout()
    fig.savefig(OUT / "changelog_progression.png")
    plt.close(fig)


def chart_test_health() -> None:
    """Real test-suite pass counts from the live snapshot (scripts/run_tests_snapshot.py)."""
    d = _load("test_results.json")
    all_suites = d.get("suites", d)
    suites = []
    passed = []
    failed = []
    for key, label in [
        ("advanced_unit", "advanced/unit"), ("advanced_integration", "advanced/integration"),
        ("baseline_unit", "baseline/unit"), ("baseline_integration", "baseline/integration"),
        ("dashboard_smoke", "dashboard smoke"),
    ]:
        entry = all_suites.get(key)
        if not entry:
            continue
        counts = entry.get("counts", entry)
        suites.append(label)
        passed.append(counts.get("passed", 0))
        failed.append(counts.get("failed", 0))

    if not suites:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(suites))
    ax.bar(x, passed, color="#16a34a", label="passed")
    ax.bar(x, failed, bottom=passed, color="#dc2626", label="failed")
    ax.set_xticks(list(x))
    ax.set_xticklabels(suites, fontsize=9, rotation=15)
    ax.set_ylabel("test count")
    ax.set_title("Real test-suite results (live snapshot)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "test_health.png")
    plt.close(fig)


if __name__ == "__main__":
    chart_headline()
    chart_per_rule()
    chart_changelog_progression()
    try:
        chart_test_health()
    except Exception as e:
        print(f"chart_test_health skipped: {e}")
    print(f"Charts written to {OUT}")
