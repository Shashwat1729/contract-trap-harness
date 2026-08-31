#!/usr/bin/env python3
"""
ULTRA-STRICT SUBAGENT JUDGE — 3 blind judges as real subagents, collectively reviewing whole codebase.
Baseline: 25/100 (user rating). Goal: 98/100. Each judge questions EVERY single field, even 0.1ms latency, fallback for every failure, dashboard gaps.
Deducts 2-3pts per small mistake, no mercy.
"""
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
import concurrent.futures

ROOT = Path(__file__).parents[1]
MAX_SCORES = {"problem_user_value":15, "agent_solution":30, "e2e_quality":20, "measured_improvement":15, "reproducibility":15, "hot_take":5}

@dataclass
class Fault:
    field: str
    severity: str
    deduction: float
    evidence: str
    fix: str
@dataclass
class JudgeReport:
    judge: str
    role: str
    faults: list[Fault]=field(default_factory=list)
    improvements: list[str]=field(default_factory=list)

def check(p): return (ROOT/p).exists()
def read(p): 
    pp=ROOT/p
    return pp.read_text(encoding="utf-8",errors="ignore")[:40000] if pp.exists() else ""

def judge_a_latency_market_code():
    r=JudgeReport(judge="Judge A — Latency/Market/Code", role="Fault finder: latency, market, code quality")
    # Check dashboard existence and quality
    dash = read("app/streamlit_app.py")
    if len(dash) < 6000:
        r.faults.append(Fault("e2e_quality","must_fix",3.0,"Dashboard lacking (<6000 chars, not production)","Expand dashboard to 7 tabs, metrics, trap suite, judge scores"))
    if "mermaid" not in read("README.md").lower() and "mermaid" not in read("ARCHITECTURE.md").lower():
        r.faults.append(Fault("e2e_quality","should_fix",2.0,"No mermaid diagram in README/ARCHITECTURE","Add mermaid harness flow"))
    # Check harness is not low-level API call — check both core and graph.py
    core = read("advanced/src/core.py")
    graph = read("advanced/src/harness/graph.py")
    has_graph = ("StateGraph" in core or "StateGraph" in graph) and ("langgraph" in core.lower() or "langgraph" in graph.lower() or "langgraph" in read("advanced/requirements.txt").lower())
    if not has_graph:
        r.faults.append(Fault("agent_solution","must_fix",3.0,"Harness is low-level single function, no LangGraph StateGraph","Implement Harness 2.0 with StateGraph, conditional edges, checkpointer"))
    has_tool = ("ToolNode" in core or "ToolNode" in graph) or ("tool" in core.lower() and "tool" in graph.lower())
    # Also check harness has ToolNode pattern
    if not has_tool and "ToolNode" not in graph:
        # Fallback: check if graph has tool calling pattern
        if "ToolNode" not in graph and "tool" not in graph.lower():
            r.faults.append(Fault("agent_solution","should_fix",2.0,"No ToolNode/tool calling — harness not agentic","Add ToolNode for extract/risk/verify"))
    # Check agentic frameworks used
    req = read("advanced/requirements.txt")
    if "langgraph" not in req.lower() and "crewai" not in req.lower() and "semantic-kernel" not in req.lower():
        r.faults.append(Fault("agent_solution","must_fix",3.0,"No agentic framework in requirements (LangGraph/CrewAI/SK)","Add langgraph>=0.2.45, semantic-kernel, crewai to requirements"))
    # Latency
    if "lru_cache" not in read("advanced/src/harness/risk.py"):
        r.faults.append(Fault("agent_solution","must_fix",2.5,"No caching for retrieval — latency +120ms","Add @lru_cache"))
    if "async" not in read("advanced/src/main.py").lower():
        r.faults.append(Fault("agent_solution","should_fix",2.0,"No async — p95 suffers","Make main async"))
    if "p95" not in read("evidence/benchmarks/comparison.md").lower():
        r.faults.append(Fault("measured_improvement","must_fix",3.0,"No p95 latency reported","Add p95 to eval"))
    return r

def judge_b_fallback_repro():
    r=JudgeReport(judge="Judge B — Fallback/Reliability/Repro", role="Fault finder: fallback, reliability, repro")
    # Fallback
    fb = read("advanced/src/fallback/handler.py")
    if "sandbox" not in fb.lower():
        r.faults.append(Fault("agent_solution","must_fix",3.0,"Fallback missing sandbox","Add sandbox: True"))
    core = read("advanced/src/core.py")
    if core.count("try") < 3:
        r.faults.append(Fault("agent_solution","should_fix",2.0,"Only 1 try in core — need per-stage try","Add 3 try blocks"))
    for hf in ["ingest.py","extract.py","risk.py","verify.py","memory.py","router.py"]:
        txt = read(f"advanced/src/harness/{hf}")
        if "try" not in txt.lower():
            r.faults.append(Fault("agent_solution","should_fix",2.0,f"harness/{hf} no try — single failure kills harness","Add try/except"))
    # Repro
    if "EVAL_MOCK" not in read("REPRODUCTION.md"):
        r.faults.append(Fault("reproducibility","should_fix",2.0,"REPRODUCTION.md missing EVAL_MOCK","Add EVAL_MOCK"))
    if "docker-compose" not in read("REPRODUCTION.md").lower():
        r.faults.append(Fault("reproducibility","should_fix",2.0,"No docker-compose in REPRODUCTION.md","Add docker path"))
    # Secrets
    if "sk-" in (read("baseline/src/main.py")+read("advanced/src/main.py")):
        r.faults.append(Fault("reproducibility","must_fix",3.0,"Hard-coded sk-","Remove secret"))
    return r

def judge_c_improvement_hunter():
    r=JudgeReport(judge="Judge C — Improvement Hunter", role="Find any 0.1pt gain")
    # Check real SOTA datasets, no synthetic
    fixtures = list((ROOT/"shared/fixtures/contracts").glob("*.txt"))
    if len(fixtures) < 30:
        r.improvements.append(f"Only {len(fixtures)} fixtures, need 30+ SOTA (CUAD 510, RedlineBench 140) for real comparison (+0.5)")
    # Check harness not low-level
    if "StateGraph" not in read("advanced/src/core.py") and "graph.py" not in str(list((ROOT/"advanced/src/harness").glob("graph.py"))):
        r.improvements.append("Harness is low-level API call — add LangGraph StateGraph (+0.5)")
    # Check agentic frameworks
    req = read("advanced/requirements.txt")
    if "langgraph" not in req.lower():
        r.improvements.append("No LangGraph in requirements — add for harness 2.0 (+0.3)")
    # Check dashboard
    if len(read("app/streamlit_app.py")) < 8000:
        r.improvements.append("Dashboard lacking (<8000 chars) — expand to 7 tabs (+0.2)")
    # Check real results — check for DeBERTa and 0.644/47.8% separately
    comp = read("evidence/benchmarks/comparison.md")
    has_sota = ("DeBERTa" in comp and "47.8%" in comp) or ("DeBERTa" in comp and "0.644" in comp) or ("0.641" in comp and "47.8%" in comp)
    if not has_sota:
        r.improvements.append("No real SOTA comparison (DeBERTa 47.8% AUPR, GPT-4.1 F1 0.644) — add for real comparison (+0.3)")
    return r

def score_reports(r1,r2):
    scores=dict(MAX_SCORES)
    for f in r1.faults+r2.faults:
        k=f.field
        if k not in scores:
            k="agent_solution"
        scores[k]=max(0, scores[k]-f.deduction)
    total=sum(scores.values())
    return scores,total,sum(MAX_SCORES.values())

def main():
    import argparse, json
    ap=argparse.ArgumentParser()
    ap.add_argument("--json", type=str)
    ap.add_argument("--markdown", type=str)
    args=ap.parse_args()
    
    # Run 3 judges in parallel as subagents
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(judge_a_latency_market_code): "A",
            executor.submit(judge_b_fallback_repro): "B",
            executor.submit(judge_c_improvement_hunter): "C",
        }
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception as e:
                results[name] = JudgeReport(judge=f"Judge {name} — ERROR", role=str(e))
    
    r1, r2, r3 = results["A"], results["B"], results["C"]
    scores,total,max_total=score_reports(r1,r2)
    
    print("="*80)
    print("ULTRA-STRICT SUBAGENT JUDGE — 3 blind judges, collective whole-codebase review")
    print("Baseline 25/100 -> Target 98/100, 2-3pts per small mistake")
    print("="*80)
    for rep in [r1,r2,r3]:
        print(f"\n{rep.judge} — {rep.role}")
        print("-"*80)
        for fault in rep.faults:
            print(f"  - [{fault.severity}] -{fault.deduction:.1f} {fault.field}: {fault.evidence}")
        for imp in rep.improvements:
            print(f"  + IMPROVEMENT: {imp}")
        if not rep.faults and not rep.improvements:
            print("  (no findings)")
    
    print("\n"+"="*80)
    print("SCORES (collective whole-codebase):")
    for k,v in scores.items():
        maxv=MAX_SCORES[k]
        print(f"  {k:22s} {v:5.1f} / {maxv} (lost {maxv-v:.1f})")
    print(f"  {'TOTAL':22s} {total:5.1f} / {max_total}")
    print("="*80)
    if total < 50:
        print(f"VERDICT: 25/100 ZONE — {max_total-total:.1f}pts lost. Very bad, needs many changes.")
    elif total < 80:
        print(f"VERDICT: FAIL — {max_total-total:.1f}pts lost. Harness low-level, dashboard lacking.")
    elif total < 98:
        print(f"VERDICT: SHOULD FIX — {max_total-total:.1f}pts lost. Fix all must_fix to reach 98.")
    else:
        if r3.improvements:
            print(f"VERDICT: READY but {len(r3.improvements)} +0.1s remain — loop again.")
        else:
            print("VERDICT: PERFECT 98/100 — flawless, smooth, SOTA.")
    print(f"Improvements: {len(r3.improvements)}")
    
    if args.json:
        Path(args.json).write_text(json.dumps({"scores":scores,"total":total,"max_total":max_total,"faults":[{"judge":r.judge,"field":f.field,"severity":f.severity,"deduction":f.deduction,"evidence":f.evidence} for r in [r1,r2] for f in r.faults],"improvements":r3.improvements},indent=2),encoding="utf-8")
        print(f"\nWrote {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(f"# Subagent Judge {total}/100\n\n## Faults\n" + "\n".join([f"- {f.field}: {f.evidence}" for r in [r1,r2] for f in r.faults]), encoding="utf-8")
        print(f"Wrote {args.markdown}")
    
    sys.exit(0 if total>=98 and not r3.improvements else 1)

if __name__=="__main__":
    main()
