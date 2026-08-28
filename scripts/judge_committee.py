#!/usr/bin/env python3
"""
Blind Judge Committee — 3 judges, very very very strict.
2 fault-finders (deduct 2-3pts per small mistake, judge EACH field)
1 improvement finder
1 scorer (weighted, deduct strictly)

Runs indefinitely until no 0.1pt improvement possible.
Usage: python scripts/judge_committee.py [--fix] [--loop]
"""
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

ROOT = Path(__file__).parents[1]

# Scoring rubric: 15+30+20+15+15+5 = 100
MAX_SCORES = {
    "problem_user_value": 15,
    "agent_solution": 30,
    "e2e_quality": 20,
    "measured_improvement": 15,
    "reproducibility": 15,
    "hot_take": 5,
}

# Each judge is blind — reads only artifacts, not internal intent
@dataclass
class Fault:
    field: str
    severity: str  # must_fix | should_fix | minor
    deduction: float  # 2-3 per small mistake
    evidence: str
    fix: str

@dataclass
class JudgeReport:
    judge: str
    role: str
    faults: list[Fault] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

def check_file_exists(path: str, required: bool = True) -> bool:
    return (ROOT / path).exists()

def read_text(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:20000]
    except:
        return ""

# ==================== JUDGE 1: Harsh Fault Finder — Claims & Evidence ====================
def judge1_claims() -> JudgeReport:
    r = JudgeReport(judge="Judge 1 — Harsh Fault Finder (Claims)", role="Find every unsupported claim, missing citation, vague metric")
    # Check README hot take exists and is specific
    readme = read_text("README.md")
    if "hot take" not in readme.lower() or "hot_take" not in readme.lower():
        # Check case
        if "Hot Take" not in readme:
            r.faults.append(Fault("hot_take", "must_fix", 3.0, "README has no Hot Take section", "Add README Hot Take with failure->lesson"))
        else:
            # Check specificity: vague?
            if len(readme) < 5000:
                r.faults.append(Fault("problem_user_value", "should_fix", 2.0, "README too short to explain user/bottleneck/value in one paragraph", "Expand README intended user + bottleneck + value per PROBLEM.md four questions"))
    # Check CHANGELOG has evidence links
    changelog = read_text("CHANGELOG.md")
    if changelog.count("evidence/") < 3:
        r.faults.append(Fault("measured_improvement", "must_fix", 3.0, "CHANGELOG has <3 evidence links — violates submission package", "Add evidence link per iteration to evidence/benchmarks/*"))
    if "REJECT" not in changelog and "removed" not in changelog.lower():
        r.faults.append(Fault("measured_improvement", "should_fix", 2.0, "CHANGELOG hides failed experiments — must include removed iteration", "Add one removed experiment per directive"))
    # Check PROBLEM.md clean extraction exists
    if not check_file_exists("PROBLEM.md"):
        r.faults.append(Fault("problem_user_value", "must_fix", 3.0, "PROBLEM.md missing", "Extract PDF to PROBLEM.md"))
    prob = read_text("PROBLEM.md")
    if "Who has this problem" not in prob:
        r.faults.append(Fault("problem_user_value", "should_fix", 2.0, "PROBLEM.md not cleanly extracted (missing four questions)", "Re-extract PDF cleanly"))
    # Check docs/00-EXECUTION-DIRECTIVE present
    if not check_file_exists("docs/00-EXECUTION-DIRECTIVE.md"):
        r.faults.append(Fault("agent_solution", "must_fix", 3.0, "Execution directive missing", "Add 12-phase directive"))
    # Check problem-brief one-paragraph test
    brief = read_text("docs/problem-brief.md")
    if "This person currently struggles" not in brief:
        r.faults.append(Fault("problem_user_value", "must_fix", 2.5, "problem-brief.md lacks one-paragraph 'This person...' test", "Add specific paragraph: X because Y causing Z, improved by A,B,C on D"))
    # Check evaluation defines primary metric before optimization
    if "Primary" not in read_text("docs/11-IMPLEMENTATION-PLAN.md"):
        r.faults.append(Fault("measured_improvement", "should_fix", 2.0, "Implementation plan has no Primary metric defined before optimization", "Define primary metric in plan §6 before code"))
    return r

# ==================== JUDGE 2: Brutal Fault Finder — Engineering & Repro ====================
def judge2_engineering() -> JudgeReport:
    r = JudgeReport(judge="Judge 2 — Brutal Fault Finder (Engineering)", role="Find every engineering sin, dummy code, missing fallback, leak")
    # Check dummy code
    for f in ["baseline/src/main.py", "advanced/src/main.py", "advanced/src/core.py", "baseline/src/core.py"]:
        txt = read_text(f)
        if any(k in txt.lower() for k in ["dummy", "phase 1 will rewrite", "todo", "placeholder", "will be replaced"]):
            r.faults.append(Fault("agent_solution", "must_fix", 3.0, f"{f} contains dummy/placeholder code", f"Replace {f} with production-grade implementation, no leaks"))
    # Check fallback exists
    if not check_file_exists("advanced/src/fallback/handler.py"):
        r.faults.append(Fault("agent_solution", "must_fix", 3.0, "advanced/src/fallback/handler.py missing — Rule 04 sandbox + human approval not implemented", "Add fallback handler per Rule 04"))
    else:
        fb = read_text("advanced/src/fallback/handler.py")
        if "sandbox" not in fb.lower():
            r.faults.append(Fault("agent_solution", "should_fix", 2.0, "fallback handler does not mention sandbox", "Add sandbox handling"))
    # Check harness is not low-level single agent call
    adv_core = read_text("advanced/src/core.py")
    if "verify_finding" not in adv_core and "VerificationResult" not in adv_core:
        r.faults.append(Fault("agent_solution", "must_fix", 3.0, "advanced/src/core.py has no verification-gated logic — harness is low-level single agent call", "Implement verification-gated closed loop per corrected thesis"))
    if "NegotiationMemory" not in adv_core and "memory" not in adv_core.lower():
        r.faults.append(Fault("agent_solution", "should_fix", 2.0, "No structured negotiation memory for turns 2-4", "Add NegotiationMemory per reviewer"))
    # Check harness files exist
    for hf in ["advanced/src/harness/ingest.py", "advanced/src/harness/extract.py", "advanced/src/harness/risk.py", "advanced/src/harness/verify.py", "advanced/src/harness/memory.py", "advanced/src/harness/router.py"]:
        if not check_file_exists(hf):
            r.faults.append(Fault("agent_solution", "must_fix", 2.5, f"{hf} missing — harness not high-functioning", f"Create {hf} production-grade"))
        else:
            if len(read_text(hf).strip()) < 300:
                r.faults.append(Fault("agent_solution", "should_fix", 2.0, f"{hf} too short (<300 chars) — likely dummy", f"Expand {hf} to production"))
    # Check synthetic vs real
    fixtures = list((ROOT / "shared/fixtures/contracts").glob("*.json")) if (ROOT / "shared/fixtures/contracts").exists() else []
    if len(fixtures) < 5:
        r.faults.append(Fault("measured_improvement", "must_fix", 3.0, f"Only {len(fixtures)} fixtures in shared/fixtures/contracts — why just 12? Need 30-50 trap suite + 140 RedlineBench for credibility (reviewer)", "Add 30-50 trap suite derived from CUAD + 20 RedlineBench samples, not just 12"))
    # Check repro
    repro = read_text("REPRODUCTION.md")
    if "make reproduce" not in repro:
        r.faults.append(Fault("reproducibility", "must_fix", 3.0, "REPRODUCTION.md has no make reproduce command", "Add clean-room steps per submission package"))
    if "EVAL_MOCK" not in repro and "mock" not in repro.lower():
        r.faults.append(Fault("reproducibility", "should_fix", 2.0, "REPRODUCTION.md has no EVAL_MOCK for offline judging", "Add EVAL_MOCK path"))
    # Check secrets
    env = read_text(".env") if check_file_exists(".env") else ""
    if env and "sk-" in env:
        r.faults.append(Fault("reproducibility", "must_fix", 3.0, ".env contains secrets and might be committed", "Ensure .env is gitignored, only .env.example committed"))
    return r

# ==================== JUDGE 3: Improvement Scout — CONDITIONAL (only report if not already done) ====================
def judge3_improvements() -> JudgeReport:
    r = JudgeReport(judge="Judge 3 — Improvement Scout", role="Find improvements, not faults; propose +0.1pt gains")
    # Check actual artifacts — only report improvement if missing
    # 1) Sirion vs surgical
    comp = read_text("evidence/benchmarks/comparison.md")
    if "Sirion" not in comp or "surgical" not in comp.lower():
        r.improvements.append("Harness vs market: Sirion does 60% faster redlining, 3x issues — add metric 'issues identified vs Sirion' and show surgical vs block edit comparison")
    # 2) 30-50 trap suite
    fixtures = list((ROOT / "shared/fixtures/contracts").glob("cuad_*.txt"))
    # also check trap suite balanced
    if len(fixtures) < 30:
        r.improvements.append("Why just 12 CUAD? Expand to 30-50 trap suite (Trap A-D interactions) + 20 RedlineBench Harbor tasks for Layer 1 credibility — improves Measured 15 by +1pt")
    else:
        # check balanced: count traps
        try:
            manifest = json.loads((ROOT / "shared/fixtures/contracts/manifest.json").read_text(encoding="utf-8"))
            total_exists = sum(1 for m in manifest for t in m.get("traps",[]) if t.get("exists"))
            if total_exists < 10:
                r.improvements.append("Trap suite has <10 traps with exists=True — not balanced for recall; inject more Trap-A/B")
        except:
            pass
    # Also check RedlineBench 20
    if not check_file_exists("shared/fixtures/contracts/redlinebench_20.json"):
        r.improvements.append("Add 20 RedlineBench Harbor tasks reference for Layer 1 credibility")
    # 3) Tier-aware
    adv_core = read_text("advanced/src/harness/memory.py")
    if "select_harness_mode" not in adv_core or "HEAT-24" not in read_text("docs/research/00-synthesis.md"):
        r.improvements.append("Add tier-aware supporting experiment: light vs balanced harness on same 20 RedlineBench tasks — shows you understood HEAT-24 paradox without making it main thesis (+0.5pt Agent)")
    else:
        # also check if eval has tier-aware experiment
        if "tier-aware" not in comp.lower() and "light vs balanced" not in comp.lower():
            # not critical, but we have code
            pass
    # 4) Secondary diagnostics
    if "Evidence-supported" not in comp or "Verification catch rate" not in comp:
        r.improvements.append("Add evidence-supported edit rate, verification catch rate, over-redlining rate as secondary diagnostics — reviewer headline needs these numbers (+1pt Measured)")
    # 5) Streamlit
    if not check_file_exists("app/streamlit_app.py"):
        r.improvements.append("Add Streamlit Harness Monitor (Extractor | Risk | Verifier | Router cards with live citations) — makes demo hackathon-type (+1pt E2E)")
    else:
        if len(read_text("app/streamlit_app.py")) < 1000:
            r.improvements.append("Streamlit monitor too short — expand to 4 cards with live citations")
    # 6) Human approval wording
    combined = read_text("docs/11-IMPLEMENTATION-PLAN.md") + read_text("docs/problem-brief.md") + read_text("ARCHITECTURE.md")
    if "before human sees it" in combined:
        r.improvements.append("Human approval wording: change 'before human sees it' to 'before recommendation reaches human reviewer as approved candidate' per reviewer (+0.2pt)")
    # 7) Only team claim
    if "only team" in combined.lower() and "not \"only team\"" not in combined.lower() and "defensible, not" not in combined.lower():
        # if claim still present as headline, not as corrected note
        if "We are the only team that gates" in combined:
            r.improvements.append("Remove 'only team' claim already fixed — keep defensible phrasing (+0.3pt)")
    # Check verification gate still
    adv = read_text("advanced/src/harness/verify.py")
    if "REJECT" not in adv or "PASS" not in adv:
        r.notes.append("Verification gate not yet produces REJECT/PASS with revise hint — implement per reviewer")
    return r

def score_reports(r1: JudgeReport, r2: JudgeReport) -> tuple[dict, float, float]:
    # Start at max, deduct per fault
    scores = dict(MAX_SCORES)
    faults = r1.faults + r2.faults
    for f in faults:
        # Map fault field to score bucket
        key = f.field
        if key not in scores:
            # Map generic fields
            if "problem" in key:
                key = "problem_user_value"
            elif "agent" in key or "harness" in key:
                key = "agent_solution"
            elif "e2e" in key or "quality" in key:
                key = "e2e_quality"
            elif "measured" in key or "trap" in key or "evidence" in key:
                key = "measured_improvement"
            elif "repro" in key:
                key = "reproducibility"
            elif "hot" in key:
                key = "hot_take"
            else:
                key = "agent_solution"
        scores[key] = max(0, scores[key] - f.deduction)
    total = sum(scores.values())
    max_total = sum(MAX_SCORES.values())
    # Also compute strictly: every small mistake is 2-3pts, so total can drop fast
    return scores, total, max_total

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="apply auto-fixes where possible")
    ap.add_argument("--loop", action="store_true", help="loop until no 0.1pt gain possible (infinite)")
    ap.add_argument("--json", type=str, help="output json path")
    args = ap.parse_args()

    r1 = judge1_claims()
    r2 = judge2_engineering()
    r3 = judge3_improvements()
    scores, total, max_total = score_reports(r1, r2)

    print("="*80)
    print("BLIND JUDGE COMMITTEE — VERY VERY VERY STRICT (2-3pts per small mistake)")
    print("="*80)
    for rep in [r1, r2, r3]:
        print(f"\n{rep.judge} — {rep.role}")
        print("-"*80)
        for fault in rep.faults:
            print(f"  - [{fault.severity}] -{fault.deduction:.1f} {fault.field}: {fault.evidence}")
            print(f"    FIX: {fault.fix}")
        for imp in rep.improvements:
            print(f"  + IMPROVEMENT: {imp}")
        for note in rep.notes:
            print(f"  * NOTE: {note}")
        if not rep.faults and not rep.improvements:
            print("  (no findings)")

    print("\n" + "="*80)
    print("SCORES (deduct 2-3 per small mistake, judge EACH field):")
    for k, v in scores.items():
        maxv = MAX_SCORES[k]
        print(f"  {k:22s} {v:5.1f} / {maxv}  (lost {maxv - v:.1f})")
    print(f"  {'TOTAL':22s} {total:5.1f} / {max_total}")
    print("="*80)
    if total < 90:
        print(f"VERDICT: FAIL — {max_total - total:.1f}pts lost. Must fix all must_fix before submission.")
    elif total < 95:
        print(f"VERDICT: SHOULD FIX — {max_total - total:.1f}pts lost. Fix should_fix for Top 3.")
    else:
        print(f"VERDICT: READY — but Improvement Scout still finds +0.1s. Loop again.")
    print(f"Improvements scout found {len(r3.improvements)} potential +0.1pt gains.")
    if args.loop:
        print("\n[LOOP MODE] Would iterate: fix -> re-test -> re-judge until no 0.1pt gain. Implement via scripts/judge_loop.sh")

    if args.json:
        out = Path(args.json)
        data = {
            "scores": scores,
            "total": total,
            "max_total": max_total,
            "faults": [{"judge": r.judge, "field": f.field, "severity": f.severity, "deduction": f.deduction, "evidence": f.evidence, "fix": f.fix} for r in [r1, r2] for f in r.faults],
            "improvements": r3.improvements,
        }
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {out}")

    # Exit code: 0 if >=95, 1 if <90, 2 if 90-95
    if total < 90:
        sys.exit(1)
    elif total < 95:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
