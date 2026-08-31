"""
Advanced core -- verification-gated harness, production-grade.

Implements reviewer-corrected closed-loop: discover -> reason -> propose -> evidence -> verify -> human review as approved candidate.
No synthetic traps as ground truth; uses RedlineBench golds + trap suite with trap-focused golds.

Verification is two independent layers, named honestly:
- Deterministic dual-threshold gate (verify.dual_verify_finding): the same regex/fuzzy
  provenance check run twice at two thresholds (strict + lenient) -- a real ensemble
  technique, but one engine, not two models. Always on, $0, no network.
- LLM cross-check (harness.llm_verify): a genuine call to LLM_MODEL (via litellm, any
  provider) that reviews the evidence in its own words and can downgrade a deterministic
  PASS to REJECT. Gated by ENABLE_LLM_VERIFY + a provider key; degrades to a no-op
  (deterministic gate only) with no key or EVAL_MOCK=1, so offline reproduction still works.

Also: self-reflective RAG via risk.self_reflective_retrieve (iterative precedent retrieval
with a coverage check), thinking logs aggregated to evidence/reviews/thinking_core.json,
Word redline generation via harness.report.generate_redlined_docx.
"""
from __future__ import annotations

import json
import os
import logging
import re
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from .harness.ingest import Page
from .harness.extract import extract_clauses, extract_clauses_hybrid, ClauseHit
from .harness.risk import assess_risk, build_evidence_package, PLAYBOOK, get_thinking_log as risk_thinking
from .harness.verify import verify_finding, dual_verify_finding, get_thinking_log as verify_thinking
from .harness.llm_verify import llm_verify_finding
from .harness.memory import NegotiationMemory, select_harness_mode
from .harness.router import route_findings
from .config import ENABLE_LLM_VERIFY, ENABLE_SEMANTIC_EXTRACTION, ENABLE_BM25_EXTRACTION, LLM_TIMEOUT, ENABLE_LANGGRAPH, LLM_VERIFY_SKIP_CONFIDENCE, ENABLE_LLM_EXTRACT, LLM_EXTRACT_MAX_CALLS

logger = logging.getLogger("advanced.core")

THINKING_LOG: list[dict[str, Any]] = []
_THINKING_MAX = 500

def _persist_dead_letter(contract_id: str, reason: str, stage: str = "unknown") -> None:
    """Persist fallback to dead-letter jsonl for human review -- ephemeral fallback never queued otherwise."""
    try:
        from pathlib import Path as _P
        dl = _P(__file__).parent.parent / "evidence" / "reviews" / "dead_letter.jsonl"
        alt = _P("evidence") / "reviews" / "dead_letter.jsonl"
        for p in (dl, alt):
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "a", encoding="utf-8") as f:
                    import json as _j, time as _t, datetime as _dt
                    _j.dump({"ts": _dt.datetime.now(_dt.timezone.utc).isoformat(), "contract_id": contract_id, "stage": stage, "reason": reason}, f)
                    f.write("\n")
                break
            except Exception:
                continue
    except Exception as e:
        logger.warning("dead_letter persist failed: %s", e)



def _log_thinking(stage: str, input_data: Any, output_data: Any, reasoning: str) -> None:
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "input": str(input_data)[:2000] if input_data is not None else None,
            "output": str(output_data)[:2000] if output_data is not None else None,
            "reasoning": reasoning,
            "mono_ms": int(time.perf_counter() * 1000),
        }
        THINKING_LOG.append(entry)
        if len(THINKING_LOG) > _THINKING_MAX:
            del THINKING_LOG[0 : len(THINKING_LOG) - _THINKING_MAX]
        logger.debug("core thinking [%s] %s", stage, reasoning[:120])
        # Persist combined
        try:
            evidence_dir = Path(__file__).parent.parent / "evidence" / "reviews"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            fp = evidence_dir / "thinking_core.json"
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(THINKING_LOG[-100:], f, indent=2, ensure_ascii=False)
        except Exception:
            try:
                alt = Path("evidence") / "reviews" / "thinking_core.json"
                alt.parent.mkdir(parents=True, exist_ok=True)
                with open(alt, "w", encoding="utf-8") as f:
                    json.dump(THINKING_LOG[-100:], f, indent=2, ensure_ascii=False)
            except Exception:
                pass
    except Exception as e:
        logger.warning("core thinking log failed: %s", e)


def get_thinking_log(limit: int = 100) -> list[dict[str, Any]]:
    try:
        return THINKING_LOG[-limit:]
    except Exception:
        return []


def save_thinking_log(path: str | Path | None = None) -> Path | None:
    try:
        p = Path(path) if path else Path(__file__).parent.parent / "evidence" / "reviews" / f"thinking_core_{int(time.time())}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(THINKING_LOG, f, indent=2, ensure_ascii=False)
        return p
    except Exception as e:
        logger.warning("save_thinking_log failed: %s", e)
        return None


# Retry for transient failures (e.g., pypdf corrupt, LLM rate limit) -- exponential backoff
def _retry_params() -> tuple[int, float, float]:
    try:
        return int(os.getenv("RETRY_MAX_ATTEMPTS", "3")), float(os.getenv("RETRY_MIN_WAIT", "1")), float(os.getenv("RETRY_MAX_WAIT", "4"))
    except Exception:
        return 3, 1.0, 4.0

def _retry_decorator() -> Any:
    attempts, min_w, max_w = _retry_params()
    return retry(stop=stop_after_attempt(attempts), wait=wait_exponential(multiplier=1, min=min_w, max=max_w), reraise=True)

@_retry_decorator()  # type: ignore[untyped-decorator]
def _retry_extract(contract_text: str, pages: list[Page]) -> list[ClauseHit]:
    # ENABLE_SEMANTIC_EXTRACTION (off by default -- see config.py) adds the real hosted-
    # embedding layer (harness/semantic.py) on top of regex; ENABLE_BM25_EXTRACTION (also
    # off by default) adds the $0 lexical layer (harness/bm25.py), fully validated on all
    # 510 real CUAD contracts (CHANGELOG #19) unlike semantic's n=7 preliminary sample.
    # Both are additive and independently gated -- extract_clauses_hybrid() degrades
    # gracefully if either is unavailable, so this is safe regardless of flag combination;
    # both flags exist so the DEFAULT reproduction stays on the certified regex-only
    # numbers until a real precision/recall trade-off is a deliberate opt-in, not a silent
    # change to every run's reported numbers.
    if ENABLE_SEMANTIC_EXTRACTION or ENABLE_BM25_EXTRACTION:
        return extract_clauses_hybrid(contract_text, pages, semantic=ENABLE_SEMANTIC_EXTRACTION, bm25=ENABLE_BM25_EXTRACTION)
    return extract_clauses(contract_text, pages)


def _trap_interactions(contract_text: str, clause_hits: list[ClauseHit], pages: list[Page]) -> list[dict[str, Any]]:
    """Find cross-clause trap interactions (A-D) -- the memorable part."""
    try:
        traps: list[dict[str, Any]] = []
        by_type: dict[str, list[ClauseHit]] = {}
        for h in clause_hits:
            by_type.setdefault(h.clause_type, []).append(h)

        # Note: (\d+) alone misses the common legal-drafting convention "thirty-six (36)
        # months" (numeral in parens after the spelled-out word) -- \(?...\)? tolerates it.
        num_re = r"\(?\s*(\d+)\s*\)?\s*{}"
        for r in by_type.get("Renewal Term", []):
            m = re.search(num_re.format("months?"), r.span_text, flags=re.IGNORECASE)
            r_val = int(m.group(1)) if m else None
            for n in by_type.get("Notice Period to Terminate Renewal", []):
                mn = re.search(num_re.format("days?"), n.span_text, flags=re.IGNORECASE)
                n_val = int(mn.group(1)) if mn else None
                if r_val is not None and n_val is not None and r_val > 12 and n_val < 60:
                    traps.append({"id": "Trap-A", "name": "Renewal vs Termination mismatch", "related": [r.clause_type, n.clause_type], "conflict": "auto-renewal >12m but notice <60d locks buyer", "spans": [r.span_text, n.span_text]})

        for c in by_type.get("Cap on Liability", []) + by_type.get("Limitation of Liability", []):
            win = contract_text[max(0, c.start - 400): c.end + 400]
            if re.search(r"carve-out|excluded from cap|not subject to limitation|shall not apply to|does not apply to", win, flags=re.IGNORECASE):
                traps.append({"id": "Trap-B", "name": "Liability cap bypass", "related": [c.clause_type], "conflict": "carve-outs bypass cap", "spans": [c.span_text]})

        for p in by_type.get("Post-Termination Services", []):
            win = contract_text[max(0, p.start - 500): p.end + 500]
            if re.search(r"delet|eras|purg", win, flags=re.IGNORECASE) and re.search(r"retain|retention|keep a copy|continue to (?:hold|store)", win, flags=re.IGNORECASE):
                traps.append({"id": "Trap-C", "name": "Deletion vs Retention conflict", "related": [p.clause_type], "conflict": "deletion obligation conflicts with transition retention", "spans": [p.span_text]})

        _log_thinking("core/trap_interactions", f"{len(clause_hits)} hits", f"{len(traps)} traps", f"Cross-clause trap scan: {len(clause_hits)} hits -> {len(traps)} interactions ({[t['id'] for t in traps]})")
        return traps
    except Exception as e:
        logger.exception("_trap_interactions failed: %s", e)
        _log_thinking("core/trap_interactions_error", str(e), "[]", f"trap_interactions exception: {e}")
        return []


def process_contract_advanced(
    contract_text: str,
    pages: list[Page],
    contract_id: str = "contract_01",
    turn: int = 1,
    memory: NegotiationMemory | None = None,
    model: str = "gpt-4o-mini",
    harness_mode: str = "auto",
    on_stage: Any = None,
) -> dict[str, Any]:
    """
    Process a contract through the verification-gated harness.

    Stages: ingest/extract -> risk (self-reflective RAG) -> evidence -> dual-verify -> human review.

    Args:
        contract_text: full contract text (up to 120k chars)
        pages: list[Page] with page:line provenance
        contract_id: contract identifier
        turn: negotiation turn 1..4
        memory: optional NegotiationMemory
        model: LLM model name for harness_mode selection
        harness_mode: auto | light | balanced | strict
        on_stage: optional callable(stage_name: str, detail: str) invoked as each real
            stage completes -- lets a caller (e.g. the SSE endpoint in main.py) stream
            genuine progress instead of a canned/fake sequence. Never raises: exceptions
            from the callback are swallowed so a slow UI can never break the harness.

    Returns:
        dict with variant, findings, approved_candidates, rejected, trap_interactions, etc.
        Never raises ValueError except for empty contract_text (preserved for test compat).
    """

    def _emit(stage: str, detail: str = "") -> None:
        if on_stage is not None:
            try:
                on_stage(stage, detail)
            except Exception:
                pass

    t_start = time.perf_counter()
    # Real per-stage latency, not the fabricated placeholder numbers a dashboard used to
    # show -- each entry is measured wall-clock ms for that stage on THIS call, aggregated
    # across the fixture suite by eval_harness.py into evidence/benchmarks/results.json.
    stage_ms: dict[str, float] = {}
    _t_prev = t_start
    if not contract_text or not contract_text.strip():
        raise ValueError("contract_text must be non-empty")
    orig_len = len(contract_text)
    if orig_len > 120000:
        contract_text = contract_text[:120000]
        logger.warning("truncation: contract %s orig_len=%d truncated_len=%d (limit 120000)", contract_id, orig_len, len(contract_text))
        _log_thinking("core/truncation", f"orig_len={orig_len}", f"truncated_len={len(contract_text)}", f"Large contract truncated {orig_len} -> {len(contract_text)} chars")

    mode = select_harness_mode(model, harness_mode)
    logger.info("harness mode=%s contract=%s turn=%s chars=%d", mode, contract_id, turn, len(contract_text))
    _log_thinking("core/start", f"contract={contract_id} turn={turn} model={model} mode={mode} chars={len(contract_text)}", "harness starting", f"process_contract_advanced start {contract_id} turn {turn} mode={mode} chars={len(contract_text)}")

    # Stage 1: ingest/extract with fallback and retry
    llm_generated_count = 0
    try:
        clause_hits = _retry_extract(contract_text, pages)
        logger.info("extracted %d clause hits", len(clause_hits))
        _emit("extract", f"{len(clause_hits)} clause hits across {len(pages)} pages")
        _log_thinking("core/extract", f"{len(contract_text)} chars, {len(pages)} pages", f"{len(clause_hits)} hits", f"Extract stage: {len(contract_text)} chars -> {len(clause_hits)} hits in {(time.perf_counter()-t_start)*1000:.1f}ms types={[h.clause_type for h in clause_hits[:5]]}")
        # LLM-as-generator (CHANGELOG #22): for playbook clause types NONE of the above
        # layers found, ask the LLM to locate a verbatim excerpt -- not retried (each
        # attempt is a real, separately-billed call; a transient failure here should
        # just mean fewer generated candidates, not 3x the cost). Never raises; each
        # returned hit already passed llm_extract's own exact-substring check and still
        # flows through the identical assess_risk/dual_verify/llm_verify gate below.
        if ENABLE_LLM_EXTRACT:
            try:
                from .harness.llm_extract import llm_extract_missing_clauses
                generated = llm_extract_missing_clauses(contract_text, pages, clause_hits, max_calls=LLM_EXTRACT_MAX_CALLS)
                llm_generated_count = len(generated)
                if generated:
                    clause_hits = clause_hits + generated
                    logger.info("llm_extract generated %d additional candidate hit(s)", len(generated))
                _emit("llm_extract", f"{len(generated)} LLM-generated candidate(s) for missing clause types")
                _log_thinking("core/llm_extract", f"{len(clause_hits) - len(generated)} existing hits", f"{len(generated)} generated", f"LLM-as-generator: {len(generated)} verbatim-verified candidate(s) added for playbook types with zero prior hits")
            except Exception as e:
                logger.warning("llm_extract_missing_clauses failed, continuing without it: %s", e)
        stage_ms["extract"] = (time.perf_counter() - _t_prev) * 1000
        _t_prev = time.perf_counter()
    except Exception as e:
        logger.exception("extract failed for %s: %s", contract_id, e)
        _log_thinking("core/extract_error", contract_id, str(e), f"Extract stage failed: {e}")
        from .fallback.handler import fallback_response
        _persist_dead_letter(contract_id, f"extract failed: {e}", stage="extract")
        # Return fallback gracefully
        return {"variant":"advanced","contract_id":contract_id,"turn":turn,"harness_mode":mode,"trap_interactions":[],"findings":[],"approved_candidates":[],"rejected":[],"trap_count":0,"total_proposed":0,"evidence_supported":0,"unsupported":0,"surgical_rate":1.0,"coverage_gaps":[],"llm_stats":{"ran":0,"confirmed":0,"flagged":0,"skipped":0,"mock":0,"skipped_high_confidence":0},"dual_stats":{"agree_pass":0,"agree_reject":0,"disagree":0},"fallback": fallback_response(contract_id, f"extract failed: {e}"), "thinking": get_thinking_log(20)}

    proposed: list[tuple[Any, ...]] = []
    try:
        for hit in clause_hits:
            try:
                finding = assess_risk(hit)
                _log_thinking("core/risk_single", f"{hit.clause_type} page {hit.page}:{hit.line}", f"finding={finding.rule_id if finding else None}", f"Risk assessed {hit.clause_type} at {hit.page}:{hit.line} -> {finding.rule_id if finding else 'no finding'}")
            except Exception as e:
                logger.warning("risk assess failed for hit %s: %s", hit.clause_type, e)
                _log_thinking("core/risk_error", hit.clause_type, str(e), f"Risk assess failed for {hit.clause_type}: {e}")
                continue
            if finding is None:
                continue
            try:
                ev_pkg = build_evidence_package(hit, finding, contract_text)
                _log_thinking("core/evidence", f"{finding.rule_id} {finding.clause_type}", f"precedent={ev_pkg.get('precedent',{}).get('id') if ev_pkg.get('precedent') else None} self_reflective={ev_pkg.get('self_reflective')}", f"Evidence package {finding.rule_id}: precedent {ev_pkg.get('precedent',{}).get('id') if ev_pkg.get('precedent') else None} coverage_complete={ev_pkg.get('self_reflective',{}).get('coverage_complete')}")
            except Exception as e:
                logger.warning("evidence package failed for %s: %s", hit.clause_type, e)
                _log_thinking("core/evidence_error", finding.rule_id, str(e), f"Evidence package failed: {e}")
                continue
            proposed.append((hit, finding, ev_pkg))
        logger.info("proposed %d findings after risk", len(proposed))
        _emit("risk", f"{len(proposed)} findings proposed via playbook + precedent retrieval")
        _log_thinking("core/risk_done", f"{len(clause_hits)} hits", f"{len(proposed)} proposed", f"Risk stage done: {len(clause_hits)} hits -> {len(proposed)} proposed findings, self-reflective RAG logged")
        stage_ms["risk"] = (time.perf_counter() - _t_prev) * 1000
        _t_prev = time.perf_counter()
    except Exception as e:
        logger.exception("risk stage failed for %s: %s", contract_id, e)
        _log_thinking("core/risk_stage_error", contract_id, str(e), f"Risk stage exception: {e}")
        from .fallback.handler import fallback_response
        _persist_dead_letter(contract_id, f"risk failed: {e}", stage="risk")
        return {"variant":"advanced","contract_id":contract_id,"turn":turn,"harness_mode":mode,"trap_interactions":[],"findings":[],"approved_candidates":[],"rejected":[],"trap_count":0,"total_proposed":0,"evidence_supported":0,"unsupported":0,"surgical_rate":1.0,"coverage_gaps":[],"llm_stats":{"ran":0,"confirmed":0,"flagged":0,"skipped":0,"mock":0,"skipped_high_confidence":0},"dual_stats":{"agree_pass":0,"agree_reject":0,"disagree":0},"fallback": fallback_response(contract_id, f"risk failed: {e}"), "thinking": get_thinking_log(20)}

    trap_interactions = _trap_interactions(contract_text, clause_hits, pages)

    # Coverage gaps: playbook rules whose trap is the ABSENCE of a clause (currently
    # P-03 "missing TFC") cannot be evidence-gated the way presence-based findings are --
    # there is no verbatim span to cite for something that is not in the document. Rather
    # than fabricate a citation to get it through dual-verify, surface it as a distinct,
    # honestly-unverified checklist flag instead of forcing it through the citation pipeline.
    coverage_gaps: list[dict[str, Any]] = []
    try:
        extracted_types = {h.clause_type for h in clause_hits}
        if "Termination for Convenience" not in extracted_types:
            p03 = PLAYBOOK["P-03"]
            coverage_gaps.append({
                "rule_id": "P-03",
                "clause_type": "Termination for Convenience",
                "gap": p03["trap"],
                "proposed_change": p03["preferred"],
                "rationale": p03["commercial"],
                "note": "No Termination for Convenience clause was found anywhere in the document. This is a checklist flag, not a citation-verified finding -- there is no span to cite for an absence, so it is not gated through dual-verify/LLM-verify and is not counted in trap_count/evidence_supported.",
            })
        _emit("coverage", f"{len(coverage_gaps)} missing-clause checklist flag(s)")
    except Exception as e:
        logger.warning("coverage_gaps check failed: %s", e)

    # Stage: verification -- deterministic dual-threshold gate (verify.dual_verify_finding
    # runs the SAME regex/fuzzy logic twice at two thresholds; it is an ensemble, not two
    # models -- see verify.py docstring), with fallback to single-threshold on exception.
    verified = []
    verification_results = []
    llm_results: list[Any] = []
    dual_stats = {"agree_pass": 0, "agree_reject": 0, "disagree": 0}
    llm_stats = {"ran": 0, "confirmed": 0, "flagged": 0, "skipped": 0, "mock": 0, "skipped_high_confidence": 0}
    for hit, finding, ev_pkg in proposed:
        try:
            # Prefer dual-verify (strict + lenient in parallel); fallback to single on exception
            try:
                ver = dual_verify_finding(hit.span_text, finding, ev_pkg, contract_text)
                _log_thinking("core/verify_dual", f"{finding.clause_type} rule={finding.rule_id}", f"{ver.status} dual_mode={ver.dual_mode} reasons={ver.reasons[:1]}", f"Dual-verify {finding.clause_type} rule={finding.rule_id}: {ver.status} mode={ver.dual_mode} in review")
                if ver.dual_mode == "dual-agree-pass":
                    dual_stats["agree_pass"] += 1
                elif ver.dual_mode == "dual-agree-reject":
                    dual_stats["agree_reject"] += 1
                elif ver.dual_mode == "dual-disagree":
                    dual_stats["disagree"] += 1
            except Exception as e:
                logger.warning("dual_verify failed for %s: %s, fallback to single", finding.clause_type, e)
                _log_thinking("core/verify_dual_fallback", finding.clause_type, str(e), f"Dual-verify fallback to single for {finding.clause_type}: {e}")
                ver = verify_finding(hit.span_text, finding, ev_pkg, contract_text)
        except Exception as e:
            logger.warning("verify failed for %s: %s", finding.clause_type, e)
            _log_thinking("core/verify_error", finding.clause_type, str(e), f"Verify exception for {finding.clause_type}: {e}")
            from .harness.verify import VerificationResult
            ver = VerificationResult(status="REJECT", reasons=[f"verify exception: {e}"], revise_hint="retry with smaller span", evidence_supported=False)

        # Real LLM cross-check: only spend a call on candidates that passed the deterministic
        # gate (why spend budget re-confirming something already rejected). A genuine network
        # call to LLM_MODEL via litellm -- degrades to a no-op when no key / EVAL_MOCK=1.
        # Confidence-based routing (CHANGELOG #20): skip the call entirely when the dual
        # verifier's strict+lenient thresholds already AGREED pass AND the playbook rule's
        # own confidence is already high -- route the real check to the findings the
        # deterministic engine is least sure about instead of spending it on every PASS.
        llm_res = None
        skip_high_confidence = (
            ver.dual_mode == "dual-agree-pass" and finding.confidence >= LLM_VERIFY_SKIP_CONFIDENCE
        )
        if ENABLE_LLM_VERIFY and ver.status == "PASS" and skip_high_confidence:
            llm_stats["skipped_high_confidence"] += 1
            _log_thinking("core/llm_verify_skip", f"{finding.clause_type} rule={finding.rule_id} confidence={finding.confidence}", "SKIPPED (high confidence)", f"LLM cross-check skipped for {finding.clause_type}: dual-agree-pass and confidence {finding.confidence} >= {LLM_VERIFY_SKIP_CONFIDENCE}, real API call not spent")
        elif ENABLE_LLM_VERIFY and ver.status == "PASS":
            try:
                llm_res = llm_verify_finding(hit.span_text, finding, ev_pkg)
                if llm_res.ran:
                    llm_stats["ran"] += 1
                    if llm_res.mock:
                        llm_stats["mock"] += 1
                    if llm_res.supported is False and (llm_res.confidence or 0) >= 0.6:
                        llm_stats["flagged"] += 1
                        ver.status = "REJECT"
                        ver.reasons = list(ver.reasons) + [f"LLM cross-check flagged: {llm_res.concern or 'unsupported per LLM review'}"]
                        ver.evidence_supported = False
                        _log_thinking("core/llm_verify", f"{finding.clause_type} rule={finding.rule_id}", "FLAGGED", f"LLM cross-check ({finding.clause_type}): model disagreed, downgraded PASS->REJECT: {llm_res.concern}")
                    else:
                        llm_stats["confirmed"] += 1
                        _log_thinking("core/llm_verify", f"{finding.clause_type} rule={finding.rule_id}", "CONFIRMED", f"LLM cross-check ({finding.clause_type}): model agreed, confidence={llm_res.confidence}")
                else:
                    llm_stats["skipped"] += 1
            except Exception as e:
                logger.warning("llm_verify_finding failed for %s: %s", finding.clause_type, e)
                llm_stats["skipped"] += 1
        verification_results.append(ver)
        llm_results.append(llm_res)
        verified.append((hit, finding, ev_pkg, ver))
    logger.info("verified %d findings, %d PASS dual_stats=%s llm_stats=%s", len(verified), sum(1 for v in verification_results if v.status=="PASS"), dual_stats, llm_stats)
    _emit("verify", f"{sum(1 for v in verification_results if v.status=='PASS')}/{len(verified)} PASS, llm_checks={llm_stats['ran']}")
    _log_thinking("core/verify_done", f"{len(verified)} findings", f"{sum(1 for v in verification_results if v.status=='PASS')} PASS dual_stats={dual_stats} llm_stats={llm_stats}", f"Verify stage done: {len(verified)} verified, {sum(1 for v in verification_results if v.status=='PASS')} PASS, dual_stats {dual_stats}, llm_stats {llm_stats}")
    # Includes the real LLM cross-check when it runs (ENABLE_LLM_VERIFY + a key) -- the
    # deterministic dual-verify and the LLM call are interleaved per-finding above, not
    # separately timed, so this one number is honest about covering both rather than
    # fabricating a split the code doesn't actually measure.
    stage_ms["verify"] = (time.perf_counter() - _t_prev) * 1000
    _t_prev = time.perf_counter()

    routed_input = []
    ver_objs = []
    for (hit, finding, ev_pkg, ver), llm_res in zip(verified, llm_results):
        d = {
            "trap_id": finding.rule_id,
            "clause_type": finding.clause_type,
            "risk": finding.risk,
            "span_text": finding.evidence_contract_span,
            "page": finding.evidence_page,
            "line": finding.evidence_line,
            "proposed_change": finding.proposed_change,
            "rationale": finding.rationale,
            "rule_id": finding.rule_id,
            "precedent_id": finding.precedent_id,
            "evidence": ev_pkg,
            "verification": ver.status,
            "reasons": ver.reasons,
            "dual_mode": getattr(ver, "dual_mode", None),
            "llm_verify": (
                {"ran": llm_res.ran, "supported": llm_res.supported, "confidence": llm_res.confidence, "concern": llm_res.concern, "mock": llm_res.mock}
                if llm_res is not None else {"ran": False, "supported": None, "confidence": None, "concern": "", "mock": True}
            ),
        }
        routed_input.append(d)
        ver_objs.append(ver)

    routed = route_findings(routed_input, ver_objs)
    _log_thinking("core/routed", f"{len(routed_input)} verified", f"{len(routed)} routed", f"Router produced {len(routed)} routed findings")
    _emit("route", f"{len(routed)} findings routed to human_review as candidates")

    findings_out = []
    for r in routed:
        f = r.finding
        findings_out.append({
            "trap_id": f["trap_id"],
            "clause_type": f["clause_type"],
            "risk": f["risk"],
            "span_text": f["span_text"],
            "page": f["page"],
            "line": f["line"],
            "proposed_change": f["proposed_change"],
            "rationale": f["rationale"],
            "rule_id": f["rule_id"],
            "precedent_id": f["precedent_id"],
            "evidence": f["evidence"],
            "verification": r.verification,
            "reasons": r.reasons,
            "route": r.route,
            "surgical": len(f["proposed_change"]) < 300,
            "dual_mode": f.get("dual_mode"),
            "llm_verify": f.get("llm_verify"),
        })

    approved = [f for f in findings_out if f["verification"] == "PASS"]
    rejected = [f for f in findings_out if f["verification"] == "REJECT"]
    stage_ms["route"] = (time.perf_counter() - _t_prev) * 1000

    if memory is not None:
        try:
            memory.update_from_findings(findings_out, turn=turn)
            _log_thinking("core/memory", f"{len(findings_out)} findings turn={turn}", f"memory open={len(memory.open_issues)}", f"Memory updated turn {turn}: {len(findings_out)} findings, open {len(memory.open_issues)}")
        except Exception as e:
            logger.warning("memory update failed: %s", e)
            _log_thinking("core/memory_error", str(e), "skip", f"Memory update failed: {e}")

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    _log_thinking("core/done", f"contract={contract_id} turn={turn}", f"approved={len(approved)} rejected={len(rejected)} latency={latency_ms}ms dual_stats={dual_stats}", f"process_contract_advanced done {contract_id} turn {turn}: {len(approved)} approved, {len(rejected)} rejected, trap_interactions {len(trap_interactions)}, latency {latency_ms}ms mode={mode}")

    # Attempt to persist combined thinking snapshot
    try:
        evidence_dir = Path(__file__).parent.parent / "evidence" / "reviews"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        snap = {
            "contract_id": contract_id,
            "turn": turn,
            "mode": mode,
            "latency_ms": latency_ms,
            "findings": len(findings_out),
            "approved": len(approved),
            "dual_stats": dual_stats,
            "core_thinking": get_thinking_log(30),
            "risk_thinking": risk_thinking(10),
            "verify_thinking": verify_thinking(10),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(evidence_dir / f"thinking_{contract_id}_t{turn}.json", "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("thinking snapshot save failed: %s", e)

    return {
        "variant": "advanced",
        "contract_id": contract_id,
        "turn": turn,
        "harness_mode": mode,
        "trap_interactions": trap_interactions,
        "findings": findings_out,
        "approved_candidates": approved,
        "rejected": rejected,
        "trap_count": len(approved),
        "total_proposed": len(findings_out),
        "evidence_supported": len(approved),
        "unsupported": len(rejected),
        "surgical_rate": sum(1 for f in findings_out if f["surgical"]) / len(findings_out) if findings_out else 1.0,
        "coverage_gaps": coverage_gaps,
        "llm_stats": llm_stats,
        "llm_extract_generated": llm_generated_count,
        "thinking": get_thinking_log(30),
        "dual_stats": dual_stats,
        "engine": "direct",
        "stage_latency_ms": {k: round(v, 2) for k, v in stage_ms.items()},
    }


def _graph_state_to_dict(result: dict[str, Any], contract_id: str, turn: int, harness_mode: str, thread_id: str) -> dict[str, Any]:
    """Convert a completed (non-interrupted) LangGraph state dict to the legacy response shape."""
    return {
        "variant": "advanced",
        "contract_id": result.get("contract_id", contract_id),
        "turn": result.get("turn", turn),
        "harness_mode": result.get("mode", harness_mode),
        "trap_interactions": result.get("trap_interactions", []),
        "findings": result.get("findings_out", []),
        "approved_candidates": result.get("approved", []),
        "rejected": result.get("rejected", []),
        "trap_count": len(result.get("approved", [])),
        "total_proposed": len(result.get("findings_out", [])),
        "evidence_supported": len(result.get("approved", [])),
        "unsupported": len(result.get("rejected", [])),
        "surgical_rate": (
            sum(1 for f in result.get("findings_out", []) if f.get("surgical")) / len(result.get("findings_out", []))
            if result.get("findings_out") else 1.0
        ),
        "coverage_gaps": result.get("coverage_gaps", []),
        "llm_stats": result.get("llm_stats", {}),
        "llm_extract_generated": next((s.get("llm_generated", 0) for s in result.get("thinking", []) if s.get("stage") == "extract"), 0),
        "thinking": result.get("thinking", []),
        "dual_stats": result.get("dual_stats", {}),
        "engine": "langgraph",
        "stage_latency_ms": result.get("stage_latency_ms", {}),
        "status": "complete",
        "thread_id": thread_id,
    }


def process_contract_graph(
    contract_text: str | None = None, pages: list[Page] | None = None, contract_id: str = "contract_01",
    turn: int = 1, memory: NegotiationMemory | None = None,
    model: str = "gpt-4o-mini", harness_mode: str = "auto",
    on_stage: Any = None, thread_id: str | None = None, engine: str = "auto",
    resume_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Graph entry — delegates to the LangGraph StateGraph (harness/graph.py), or falls
    back to the direct pipeline.

    engine: "auto" (default) respects the global ENABLE_LANGGRAPH flag; "graph" forces a
        graph-mode attempt for this one call regardless of the global flag (still falls
        back to direct on any graph-invoke exception); "direct" forces the direct path.
        Lets a single caller (the API, the dashboard) offer graph mode as an opt-in
        without changing the process-wide default that `make reproduce` depends on.

    resume_decision: when set, this call resumes a PREVIOUSLY interrupted graph run at the
        same thread_id (see ENABLE_GRAPH_INTERRUPT / harness/graph.py::human_review_node's
        real interrupt() call) instead of starting a new one -- contract_text/pages are not
        needed for a resume since the checkpointer already has them. Shape:
        {"approve_keys": [override_key, ...]} -- the "override_key" values come from the
        earlier pending-review response's "interrupt.pending_rejected[*].override_key".
        If the graph run at thread_id was never interrupted, this raises (there is nothing
        to resume).
    """
    if resume_decision is not None:
        from .harness.graph import build_graph
        from langgraph.types import Command
        graph = build_graph()
        tid = thread_id or contract_id
        config = {"configurable": {"thread_id": tid}}
        result = graph.invoke(Command(resume=resume_decision), config=config)
        if "__interrupt__" in result:
            return _pending_review_response(result, contract_id, turn, harness_mode, tid)
        return _graph_state_to_dict(result, contract_id, turn, harness_mode, tid)

    if contract_text is None or pages is None:
        raise ValueError("contract_text and pages are required unless resume_decision is set")

    use_graph = engine == "graph" or (engine == "auto" and ENABLE_LANGGRAPH)
    if not use_graph:
        result = process_contract_advanced(contract_text, pages, contract_id, turn, memory, model, harness_mode, on_stage)
        result["engine"] = "direct"
        return result
    try:
        from .harness.graph import build_graph
        graph = build_graph()
        init_state = {
            "contract_text": contract_text, "pages": pages, "contract_id": contract_id,
            "turn": turn, "mode": harness_mode, "clause_hits": [], "trap_interactions": [],
            "coverage_gaps": [], "proposed": [], "verified": [], "verification_results": [],
            "llm_results": [], "dual_stats": {}, "llm_stats": {}, "routed": [], "findings_out": [],
            "approved": [], "rejected": [], "thinking": [], "latency_ms": 0, "stage_latency_ms": {}, "error": None, "dead_letter": None, "retry_count": 0,
        }
        # A fresh run must get a fresh thread_id, never bare contract_id: build_graph()'s
        # checkpointer is now a process-lifetime singleton (required for real interrupt/
        # resume to work -- see build_graph()'s docstring), so re-invoking the SAME
        # thread_id a second time does not start clean -- HarnessState's Annotated[...,
        # operator.add] accumulator fields (clause_hits, thinking) silently carry forward
        # the PRIOR run's values into the new one. Verified directly: re-invoking the same
        # thread_id with a different contract left the old contract's clause_hits mixed
        # into the new run's result. Only an explicit caller-supplied thread_id (a genuine
        # resume, which always passes the id from the original interrupt response) reuses
        # one on purpose.
        tid = thread_id or f"{contract_id}:{uuid.uuid4().hex[:12]}"
        config = {"configurable": {"thread_id": tid}}
        result = graph.invoke(init_state, config=config)
        if "__interrupt__" in result:
            return _pending_review_response(result, contract_id, turn, harness_mode, tid)
        return _graph_state_to_dict(result, contract_id, turn, harness_mode, tid)
    except Exception as e:
        logger.exception("graph invoke failed, fallback to direct: %s", e)
        result = process_contract_advanced(contract_text, pages, contract_id, turn, memory, model, harness_mode, on_stage)
        result["engine"] = "direct-fallback"
        return result


def _pending_review_response(result: dict[str, Any], contract_id: str, turn: int, harness_mode: str, thread_id: str) -> dict[str, Any]:
    """A real langgraph interrupt() fired inside human_review_node (ENABLE_GRAPH_INTERRUPT=1,
    at least one REJECTed finding) -- the graph is PAUSED, not finished. Return a distinct
    shape (status="pending_human_review") rather than pretending this is a completed result;
    the caller resumes with process_contract_graph(resume_decision=..., thread_id=thread_id)."""
    payload = result["__interrupt__"][0].value
    return {
        "variant": "advanced", "contract_id": contract_id, "turn": turn, "harness_mode": harness_mode,
        "engine": "langgraph", "status": "pending_human_review", "thread_id": thread_id,
        "interrupt": payload,
        "trap_interactions": [], "findings": [], "approved_candidates": [], "rejected": [],
        "trap_count": 0, "total_proposed": 0, "evidence_supported": 0, "unsupported": 0,
        "surgical_rate": 1.0, "coverage_gaps": [], "llm_stats": {}, "dual_stats": {}, "thinking": [],
        "stage_latency_ms": {},
    }

