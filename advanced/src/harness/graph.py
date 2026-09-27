"""
Harness 2.0 — LangGraph StateGraph for Contract Trap Harness

Implements verification-gated closed loop as a declarative StateGraph, not a single
function. Feature-flagged behind ENABLE_LANGGRAPH (default 0) so `make reproduce` stays
on the fully-validated direct path; this is an opt-in execution mode, exposed in the
dashboard as "Agentic (LangGraph)" mode so a reviewer can actually see it run.

State: TypedDict HarnessState with Annotated reducers
Nodes: extract -> risk -> evidence -> verify -> [revise -> verify]* -> human_review
Edges: conditional should_revise (REJECT with a revise_hint, one retry) routes through a
    real revise node (see revise_node) that mechanically rewrites the rejected finding
    based on *why* it failed, then re-enters verify -- not a no-op replay of the same
    computation.
Checkpointer: InMemorySaver (default) / SqliteSaver
Observability: thinking log entries per node, aggregated the same way as core.py's
    direct path (evidence/reviews/thinking_core.json).
"""
from __future__ import annotations

import logging
import time
from typing import TypedDict, Annotated, Optional, Literal, Any
import operator

logger = logging.getLogger("advanced.harness.graph")

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    logger.warning(f"LangGraph not available (fallback to direct function): {e}")

from .ingest import Page
from .extract import ClauseHit, SAAS_TYPES
from .risk import RiskFinding


class HarnessState(TypedDict):
    contract_text: str
    pages: list[Page]
    contract_id: str
    turn: int
    mode: str
    clause_hits: Annotated[list[ClauseHit], operator.add]
    trap_interactions: list[dict[str, Any]]
    coverage_gaps: list[dict[str, Any]]
    proposed: list[tuple[Any, ...]]
    verified: list[tuple[Any, ...]]
    verification_results: list[Any]
    llm_results: list[Any]
    dual_stats: dict[str, Any]
    llm_stats: dict[str, Any]
    routed: list[Any]
    findings_out: list[dict[str, Any]]
    approved: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    thinking: Annotated[list[dict[str, Any]], operator.add]
    latency_ms: int
    stage_latency_ms: dict[str, float]
    error: Optional[str]
    dead_letter: Optional[dict[str, Any]]
    retry_count: int


def extract_node(state: HarnessState) -> dict[str, Any]:
    """Node 1: extract clauses -- same path as the direct pipeline (regex, or regex+semantic
    hybrid when ENABLE_SEMANTIC_EXTRACTION is on, with retry) via core._retry_extract, so
    graph mode and direct mode see identical clause extraction."""
    t0 = time.perf_counter()
    try:
        from ..core import _retry_extract
        from ..config import ENABLE_LLM_EXTRACT, LLM_EXTRACT_MAX_CALLS
        hits = _retry_extract(state["contract_text"], state["pages"])
        generated_count = 0
        # LLM-as-generator parity with core.py's direct pipeline (CHANGELOG #22) -- same
        # flag, same cap, same downstream gate (assess_risk/dual_verify/llm_verify below
        # sees no difference between a regex/semantic/BM25 hit and an llm_generated one).
        if ENABLE_LLM_EXTRACT:
            try:
                from .llm_extract import llm_extract_missing_clauses
                generated = llm_extract_missing_clauses(state["contract_text"], state["pages"], hits, max_calls=LLM_EXTRACT_MAX_CALLS)
                generated_count = len(generated)
                if generated:
                    hits = hits + generated
            except Exception as e:
                logger.warning("extract_node: llm_extract failed, continuing without it: %s", e)
        logger.info("extract_node: %d hits (%d llm-generated)", len(hits), generated_count)
        stage_ms = dict(state.get("stage_latency_ms", {}))
        stage_ms["extract"] = round((time.perf_counter() - t0) * 1000, 2)
        return {"clause_hits": hits, "stage_latency_ms": stage_ms, "thinking": [{"stage": "extract", "hits": len(hits), "llm_generated": generated_count}]}
    except Exception as e:
        logger.exception("extract_node failed: %s", e)
        return {"clause_hits": [], "error": str(e), "thinking": [{"stage": "extract", "error": str(e)}]}


def risk_node(state: HarnessState) -> dict[str, Any]:
    """Node 2: playbook risk assessment + self-reflective RAG evidence retrieval per hit."""
    t0 = time.perf_counter()
    try:
        from .risk import assess_risk, build_evidence_package
        proposed = []
        for hit in state.get("clause_hits", []):
            finding = assess_risk(hit)
            if finding is None:
                continue
            pkg = build_evidence_package(hit, finding, state["contract_text"])
            proposed.append((hit, finding, pkg))
        logger.info("risk_node: %d proposed", len(proposed))
        stage_ms = dict(state.get("stage_latency_ms", {}))
        stage_ms["risk"] = round((time.perf_counter() - t0) * 1000, 2)
        return {"proposed": proposed, "stage_latency_ms": stage_ms, "thinking": [{"stage": "risk", "proposed": len(proposed)}]}
    except Exception as e:
        logger.exception("risk_node failed: %s", e)
        return {"proposed": [], "error": str(e)}


def evidence_node(state: HarnessState) -> dict[str, Any]:
    """Node 3: cross-clause trap interactions + playbook coverage gaps."""
    t0 = time.perf_counter()
    try:
        from ..core import _trap_interactions, _coverage_gaps
        traps = _trap_interactions(state["contract_text"], state.get("clause_hits", []), state["pages"])
        # Same absence-based checklist as the direct pipeline (P-03 only -- a missing
        # clause of any other type is not a playbook trap), same shape.
        gaps = _coverage_gaps(state.get("clause_hits", []))
        # Folded into the "risk" bucket: cross-clause/coverage analysis over the same
        # clause_hits risk_node already scored, matching the direct pipeline's single
        # "risk" stage_ms bucket rather than inventing a stage key the direct path lacks.
        stage_ms = dict(state.get("stage_latency_ms", {}))
        stage_ms["risk"] = round(stage_ms.get("risk", 0.0) + (time.perf_counter() - t0) * 1000, 2)
        return {"trap_interactions": traps, "coverage_gaps": gaps, "stage_latency_ms": stage_ms, "thinking": [{"stage": "evidence", "traps": len(traps), "gaps": len(gaps)}]}
    except Exception as e:
        logger.exception("evidence_node failed: %s", e)
        return {"trap_interactions": [], "coverage_gaps": []}


def verify_node(state: HarnessState) -> dict[str, Any]:
    """Node 4: verification -- deterministic dual-threshold gate (verify.dual_verify_finding,
    the same regex/fuzzy check run twice at two thresholds, an ensemble not two models) plus
    the real LLM cross-check (ENABLE_LLM_VERIFY + a provider key; degrades to a no-op with no
    key / EVAL_MOCK=1). Mirrors core.py's process_contract_advanced verify stage exactly so
    graph mode is not a weaker verification path than the direct one."""
    t0 = time.perf_counter()
    try:
        from .verify import verify_finding, dual_verify_finding, VerificationResult
        from .llm_verify import llm_cross_check, new_llm_stats
        from ..config import ENABLE_LLM_VERIFY, LLM_VERIFY_SKIP_CONFIDENCE
        contract_text = state["contract_text"]
        verified = []
        results = []
        llm_results: list[Any] = []
        dual_stats = {"agree_pass": 0, "agree_reject": 0, "disagree": 0}
        llm_stats = new_llm_stats()

        for hit, finding, pkg in state.get("proposed", []):
            try:
                ver = dual_verify_finding(hit.span_text, finding, pkg, contract_text)
                if ver.dual_mode == "dual-agree-pass":
                    dual_stats["agree_pass"] += 1
                elif ver.dual_mode == "dual-agree-reject":
                    dual_stats["agree_reject"] += 1
                elif ver.dual_mode == "dual-disagree":
                    dual_stats["disagree"] += 1
            except Exception as e:
                logger.warning("verify_node dual_verify failed for %s: %s, fallback to single", finding.clause_type, e)
                try:
                    ver = verify_finding(hit.span_text, finding, pkg, contract_text)
                except Exception as e2:
                    ver = VerificationResult(status="REJECT", reasons=[f"verify exception: {e2}"], revise_hint="retry with smaller span", evidence_supported=False)

            # Same LLM cross-check stage as core.py (shared helper, so the engines cannot drift).
            llm_res = llm_cross_check(
                hit.span_text, finding, pkg, ver, llm_stats,
                enabled=ENABLE_LLM_VERIFY, skip_confidence=LLM_VERIFY_SKIP_CONFIDENCE,
            )

            verified.append((hit, finding, pkg, ver))
            results.append(ver)
            llm_results.append(llm_res)

        logger.info("verify_node: %d verified, %d PASS, dual_stats=%s llm_stats=%s", len(verified), sum(1 for r in results if r.status == "PASS"), dual_stats, llm_stats)
        stage_ms = dict(state.get("stage_latency_ms", {}))
        stage_ms["verify"] = round(stage_ms.get("verify", 0.0) + (time.perf_counter() - t0) * 1000, 2)
        return {
            "verified": verified,
            "verification_results": results,
            "llm_results": llm_results,
            "dual_stats": dual_stats,
            "llm_stats": llm_stats,
            "stage_latency_ms": stage_ms,
            "thinking": [{"stage": "verify", "verified": len(verified), "pass": sum(1 for r in results if r.status == "PASS")}],
        }
    except Exception as e:
        logger.exception("verify_node failed: %s", e)
        return {"verified": [], "verification_results": [], "llm_results": [], "dual_stats": {}, "llm_stats": {}}


def _shorten_surgical(text: str, limit: int = 280) -> str:
    """Mechanically shrink a block edit to a surgical one: the first sentence/clause under
    `limit` chars, falling back to a word-boundary truncation. Used only by revise_node,
    after verify.py has already rejected the original for being a block edit (>500-700
    chars) -- a real edit to the finding, not a relabeling of the same text."""
    if not text or len(text) <= limit:
        return text
    import re
    m = re.match(r"^(.{1," + str(limit) + r"}[.;])\s", text)
    if m:
        return m.group(1)
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut + "…") if cut else text[:limit]


def revise_node(state: HarnessState) -> dict[str, Any]:
    """Real self-correction after a REJECT verdict -- the "Reflection" agentic design pattern
    (an actor step's output is critiqued by a separate evaluator step, then the actor revises
    based on that specific critique before retrying; see Shinn et al., "Reflexion:
    Language Agents with Verbal Reinforcement Learning", 2023, and Anthropic's own agentic-
    patterns writeups) applied here with `verify_node` as the evaluator and this node as the
    actor -- not a re-run of the identical computation, and not blind retry-until-pass. Each
    rejected finding is mechanically revised based on *why* verify.py rejected it, then
    re-enters verify:
      - "not surgical" (proposed_change too long) -> shortened to the first clause/sentence
        under the surgical limit (see _shorten_surgical) -- a real edit to the finding.
      - missing precedent / empty contract_span -> evidence package rebuilt with a deeper
        self-reflective retrieval pass (max_iterations 2 -> 4) instead of repeating the exact
        search that already failed.
    Findings that already PASSed are carried through unchanged. Capped to one pass by
    should_revise's retry_count < 1 check, so this cannot loop forever."""
    try:
        from .risk import build_evidence_package
        from dataclasses import replace as _replace

        proposed = state.get("proposed", [])
        results = state.get("verification_results", [])
        revised: list[tuple[Any, ...]] = []
        n_revised = 0

        for (hit, finding, pkg), ver in zip(proposed, results):
            if getattr(ver, "status", "") != "REJECT":
                revised.append((hit, finding, pkg))
                continue
            reason_text = " ".join(getattr(ver, "reasons", []) or [])
            new_finding, new_pkg = finding, pkg

            if "not surgical" in reason_text or "split into smaller edits" in reason_text:
                shortened = _shorten_surgical(finding.proposed_change)
                if shortened != finding.proposed_change:
                    new_finding = _replace(finding, proposed_change=shortened)
                    n_revised += 1

            if "precedent" in reason_text or "contract_span" in reason_text:
                try:
                    new_pkg = build_evidence_package(hit, new_finding, state["contract_text"], max_iterations=4)
                    n_revised += 1
                except Exception:
                    new_pkg = pkg

            revised.append((hit, new_finding, new_pkg))

        logger.info("revise_node: %d/%d rejected findings mechanically revised", n_revised, sum(1 for v in results if getattr(v, "status", "") == "REJECT"))
        return {
            "proposed": revised,
            "retry_count": state.get("retry_count", 0) + 1,
            "thinking": [{"stage": "revise", "revised": n_revised, "of": len(proposed)}],
        }
    except Exception as e:
        logger.exception("revise_node failed: %s", e)
        return {"retry_count": state.get("retry_count", 0) + 1, "thinking": [{"stage": "revise", "error": str(e)}]}


def human_review_node(state: HarnessState) -> dict[str, Any]:
    """Node 5: route verified findings; always human_review (see router.py -- Rule 04/05
    safety design, never auto-approve a redline)."""
    t0 = time.perf_counter()
    try:
        from .router import route_findings
        from .llm_verify import llm_result_dict
        from ..config import ENABLE_GRAPH_INTERRUPT
        verified = state.get("verified", [])
        llm_results = state.get("llm_results") or [None] * len(verified)
        routed_input = []
        ver_objs = []
        for (hit, finding, pkg, ver), llm_res in zip(verified, llm_results):
            d = {
                "trap_id": finding.rule_id, "clause_type": finding.clause_type, "risk": finding.risk,
                "span_text": finding.evidence_contract_span, "page": finding.evidence_page, "line": finding.evidence_line,
                "proposed_change": finding.proposed_change, "rationale": finding.rationale, "rule_id": finding.rule_id,
                "precedent_id": finding.precedent_id, "evidence": pkg, "verification": ver.status, "reasons": ver.reasons,
                "dual_mode": getattr(ver, "dual_mode", None),
                "llm_verify": llm_result_dict(llm_res),
            }
            routed_input.append(d)
            ver_objs.append(ver)
        routed = route_findings(routed_input, ver_objs)
        findings_out = [{
            "trap_id": r.finding["trap_id"], "clause_type": r.finding["clause_type"], "risk": r.finding["risk"],
            "span_text": r.finding["span_text"], "page": r.finding["page"], "line": r.finding["line"],
            "proposed_change": r.finding["proposed_change"], "rationale": r.finding["rationale"], "rule_id": r.finding["rule_id"],
            "precedent_id": r.finding["precedent_id"], "evidence": r.finding["evidence"], "verification": r.verification,
            "reasons": r.reasons, "route": r.route, "surgical": len(r.finding["proposed_change"]) < 300,
            "dual_mode": r.finding.get("dual_mode"), "llm_verify": r.finding.get("llm_verify"),
        } for r in routed]
        approved = [f for f in findings_out if f["verification"] == "PASS"]
        rejected = [f for f in findings_out if f["verification"] == "REJECT"]

        # Composite key, not a bare rule_id: two findings can share a rule_id (e.g. two
        # separate Renewal Term regex hits), and -- found via a real dashboard UI test
        # driving this end to end, not by inspection -- can even share the exact same
        # page:line (two overlapping regex patterns matching the same clause header).
        # The trailing index guarantees uniqueness regardless, so this can never collide
        # into a duplicate Streamlit widget key or an ambiguous human decision.
        for i, f in enumerate(rejected):
            f["override_key"] = f"{f['clause_type']}|{f['rule_id']}|{f['page']}|{f['line']}|{i}"

        if ENABLE_GRAPH_INTERRUPT and LANGGRAPH_AVAILABLE and rejected:
            from langgraph.types import interrupt
            decision = interrupt({
                "kind": "human_review_required",
                "contract_id": state["contract_id"],
                "pending_rejected": [
                    {"override_key": f["override_key"], "clause_type": f["clause_type"], "risk": f["risk"],
                     "reasons": f["reasons"], "proposed_change": f["proposed_change"]}
                    for f in rejected
                ],
                "approved_count": len(approved),
            })
            # Resume value: {"approve_keys": [override_key, ...]} -- a human explicitly
            # overriding specific machine REJECTs to approved. Never silent: every override
            # is marked verification="PASS (human override)" and human_override=True so the
            # audit trail always shows a human, not the deterministic gate, made this call.
            approve_keys = set((decision or {}).get("approve_keys", [])) if isinstance(decision, dict) else set()
            still_rejected = []
            for f in rejected:
                if f["override_key"] in approve_keys:
                    f["verification"] = "PASS (human override)"
                    f["human_override"] = True
                    approved.append(f)
                else:
                    f["human_override"] = False
                    still_rejected.append(f)
            rejected = still_rejected
            logger.info("human_review resumed for %s: %d human-approved, %d still rejected", state["contract_id"], len(approve_keys), len(rejected))

        stage_ms = dict(state.get("stage_latency_ms", {}))
        stage_ms["route"] = round((time.perf_counter() - t0) * 1000, 2)
        return {"routed": routed, "findings_out": findings_out, "approved": approved, "rejected": rejected, "stage_latency_ms": stage_ms, "thinking": [{"stage": "human_review", "approved": len(approved), "rejected": len(rejected)}]}
    except Exception as e:
        # GraphInterrupt is langgraph's own control-flow signal for a real interrupt()
        # pause (see above) -- it is an Exception subclass, so the broad handler below
        # would otherwise silently swallow a legitimate pause and report it as a node
        # failure. Must always propagate, never be treated as an error.
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        logger.exception("human_review failed: %s", e)
        return {"findings_out": [], "approved": [], "rejected": []}


def should_revise(state: HarnessState) -> Literal["revise", "human_review"]:
    """Conditional edge: REJECT with a revise_hint and no retry spent yet -> revise once."""
    fails = [v for v in state.get("verification_results", []) if getattr(v, "status", "") == "REJECT" and getattr(v, "revise_hint", None)]
    retry = state.get("retry_count", 0)
    if fails and retry < 1:
        return "revise"
    return "human_review"


_CACHED_GRAPH: Any = None
_GRAPH_LOCK = __import__("threading").Lock()


def build_graph() -> Any:
    """Build and compile the StateGraph. Feature-flagged, lazy import.

    Cached as a process-lifetime singleton, NOT rebuilt on every call. This matters for
    more than performance: real interrupt()/resume (human_review_node, ENABLE_GRAPH_
    INTERRUPT=1) requires the SAME checkpointer instance to still hold the paused run's
    state when a later, separate process_contract_graph(resume_decision=...) call comes
    in -- real HTTP traffic always makes these as two independent calls (the initial
    /api/redline request, then a later /api/harness/resume request). Rebuilding
    build_graph() (and therefore a fresh, empty InMemorySaver()) on every call silently
    discarded the paused state between those two calls -- found by the first real
    end-to-end interrupt/resume integration test through the actual API
    (test_redline_graph_engine_real_interrupt_and_resume), not by inspection. See
    CHANGELOG #21.
    """
    global _CACHED_GRAPH
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("langgraph not installed — run pip install langgraph")
    with _GRAPH_LOCK:
        if _CACHED_GRAPH is not None:
            return _CACHED_GRAPH

        from langgraph.graph import StateGraph, START, END
        from ..config import LANGGRAPH_CHECKPOINTER
        checkpointer: Any = None
        if LANGGRAPH_CHECKPOINTER == "sqlite":
            # Real, file-backed persistence -- survives a process restart, unlike
            # InMemorySaver. Matters for human-in-the-loop: a reviewer may take far
            # longer to respond than one API process's uptime.
            try:
                import sqlite3
                from pathlib import Path
                from langgraph.checkpoint.sqlite import SqliteSaver
                db_path = Path(__file__).parents[3] / "evidence" / "checkpoints" / "langgraph.sqlite"
                db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(db_path), check_same_thread=False)
                checkpointer = SqliteSaver(conn)
            except Exception as e:
                logger.warning("sqlite checkpointer unavailable (%s), falling back to in-memory", e)
        if checkpointer is None:
            try:
                from langgraph.checkpoint.memory import InMemorySaver
                checkpointer = InMemorySaver()
            except Exception:
                checkpointer = None

        builder = StateGraph(HarnessState)
        builder.add_node("extract", extract_node)
        builder.add_node("risk", risk_node)
        builder.add_node("evidence", evidence_node)
        builder.add_node("verify", verify_node)
        builder.add_node("revise", revise_node)
        builder.add_node("human_review", human_review_node)

        builder.add_edge(START, "extract")
        builder.add_edge("extract", "risk")
        builder.add_edge("risk", "evidence")
        builder.add_edge("evidence", "verify")
        builder.add_conditional_edges("verify", should_revise, {"revise": "revise", "human_review": "human_review"})
        builder.add_edge("revise", "verify")
        builder.add_edge("human_review", END)

        _CACHED_GRAPH = builder.compile(checkpointer=checkpointer) if checkpointer else builder.compile()
        return _CACHED_GRAPH
