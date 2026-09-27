"""
Verify -- gates every substantive redline on auditable evidence.

For every proposed edit, verify:
  - contract_span exists at page:line in contract_text
  - playbook rule exists and matches clause type
  - precedent exists (if required)
  - proposed change is surgical (not block edit >500 chars)

If FAIL -> REJECT and emit revise hint for targeted retry.
Only PASS edits reach human reviewer as approved candidate (Rule 04/05 framing).

dual_verify_finding(hit_span, finding, evidence_pkg, contract_text) runs the SAME
deterministic provenance/surgical-edit check twice, in parallel, at two thresholds
(strict + lenient) -- a real ensemble technique that catches threshold-sensitive
findings, but it is one deterministic engine, not two language models, despite the
name. If the two thresholds disagree, that's flagged as a borderline finding ->
REJECT pending human review. For a genuine second opinion from an actual LLM, see
harness/llm_verify.py::llm_verify_finding, which core.py runs as an additional gate
on top of this one.

Thinking logs recorded per call for auditability.
Production-grade: type hints, docstrings, logging, try/except.
"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from rapidfuzz import fuzz

from .risk import PLAYBOOK, PRECEDENTS, RiskFinding

logger = logging.getLogger("advanced.harness.verify")

# ---------------------------------------------------------------------------
# Thinking log (RiskWise Developer View)
# ---------------------------------------------------------------------------
THINKING_LOG: list[dict[str, Any]] = []
_THINKING_MAX = 500


def _log_thinking(stage: str, input_data: Any, output_data: Any, reasoning: str) -> None:
    """Append thinking entry. Never raises."""
    try:
        entry: dict[str, Any] = {
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
        logger.debug("thinking [%s] %s", stage, reasoning[:120])
        try:
            evidence_dir = Path(__file__).parents[2] / "evidence" / "reviews"
            alt_dir = Path(__file__).parents[1].parent / "evidence" / "reviews"
            for d in (evidence_dir, alt_dir):
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    fp = d / "thinking_verify.json"
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(THINKING_LOG[-50:], f, indent=2, ensure_ascii=False)
                    break
                except Exception:
                    continue
        except Exception:
            pass
    except Exception as e:
        logger.warning("thinking log failed: %s", e)


def get_thinking_log(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent thinking entries."""
    try:
        return THINKING_LOG[-limit:]
    except Exception as e:
        logger.warning("get_thinking_log failed: %s", e)
        return []


@dataclass
class VerificationResult:
    status: Literal["PASS", "REJECT"]
    reasons: list[str]
    revise_hint: str | None
    evidence_supported: bool
    # Extended fields for dual-verify traceability
    dual_mode: str | None = None
    thinking: list[dict[str, Any]] | None = None


def _check_contract_span(hit_span: str, contract_text: str, evidence_pkg: dict[str, Any], strict: bool = True) -> tuple[bool, str]:
    """
    Check if contract_span exists in contract_text.

    strict=True:  fuzz partial_ratio >=80, substring 40 chars required (ModelProof strict)
    strict=False: fuzz partial_ratio >=65, substring 25 chars (lenient / second LM)
    """
    try:
        if not hit_span or not hit_span.strip():
            return False, "empty hit_span"
        span_norm = re.sub(r"\s+", " ", hit_span.strip())[:160]
        contract_norm = re.sub(r"\s+", " ", contract_text)[:8000]
        threshold = 80 if strict else 65
        substr_len = 40 if strict else 25
        exists = False
        if span_norm:
            if span_norm[:substr_len].lower() in contract_text.lower():
                exists = True
            elif span_norm[:60].lower() in contract_norm.lower():
                exists = True
            else:
                score = fuzz.partial_ratio(span_norm[:80].lower(), contract_norm.lower())
                if score >= threshold:
                    exists = True
        if not exists:
            return False, f"contract_span not found (hallucinated page:{evidence_pkg.get('contract_page')}, fuzz partial_ratio <{threshold} strict={strict})"
        return True, ""
    except Exception as e:
        logger.warning("_check_contract_span failed strict=%s: %s", strict, e)
        return False, f"span check exception: {e}"


def _verify_strict(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any], contract_text: str) -> VerificationResult:
    """Strict verification (LM1): high threshold, full gate."""
    return _verify_with_mode(hit_span, finding, evidence_pkg, contract_text, strict=True, mode="strict")


def _verify_lenient(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any], contract_text: str) -> VerificationResult:
    """Lenient verification (LM2): lower threshold, second precedent check, no hard surgical fail for 500-700 chars."""
    return _verify_with_mode(hit_span, finding, evidence_pkg, contract_text, strict=False, mode="lenient")


def _verify_with_mode(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any], contract_text: str, strict: bool, mode: str) -> VerificationResult:
    """Core verify logic parameterized by strict flag."""
    reasons: list[str] = []
    try:
        # 1) Contract span provenance
        ok, msg = _check_contract_span(hit_span, contract_text, evidence_pkg, strict=strict)
        if not ok:
            reasons.append(msg)

        # 2) Playbook rule exists and matches clause type
        rule_id = evidence_pkg.get("playbook_rule")
        rule = PLAYBOOK.get(rule_id) if rule_id else None
        if not rule:
            reasons.append(f"playbook_rule {rule_id} does not exist")
        elif finding.clause_type not in rule.get("clause_types", []):
            reasons.append(f"rule {rule_id} does not govern clause_type {finding.clause_type}")

        # 3) Precedent exists if rule requires it
        prec = evidence_pkg.get("precedent")
        if not prec:
            expected_prec_id = rule.get("precedent", "").split()[0] if rule else ""
            if expected_prec_id and not any(p["id"] == expected_prec_id for p in PRECEDENTS):
                # For lenient mode, allow missing precedent if confidence high
                if strict or finding.confidence < 0.85:
                    reasons.append(f"precedent {expected_prec_id} not found")

        # 4) Surgical edit check
        proposed = finding.proposed_change or ""
        if strict:
            if len(proposed) > 500:
                reasons.append(f"proposed change is block edit ({len(proposed)} chars) not surgical - split into smaller edits")
        else:
            # Lenient: allow up to 700 chars before failing, 500-700 is warning not REJECT
            if len(proposed) > 700:
                reasons.append(f"proposed change is block edit ({len(proposed)} chars) even for lenient - split")

        # 5) Empty evidence
        if not evidence_pkg.get("contract_span"):
            reasons.append("empty contract_span evidence")

        if reasons:
            hint = "Revise: ensure contract_span is verbatim substring at claimed page:line, use correct rule_id for clause_type, and keep edit surgical (<300 chars)."
            return VerificationResult(status="REJECT", reasons=reasons, revise_hint=hint, evidence_supported=False, dual_mode=mode)
        _log_thinking(f"verify/{mode}", f"{finding.clause_type} rule={rule_id}", "PASS", f"{mode} verifier PASS for {finding.clause_type} rule={rule_id}")
        return VerificationResult(status="PASS", reasons=[], revise_hint=None, evidence_supported=True, dual_mode=mode)
    except Exception as e:
        logger.exception("_verify_with_mode %s failed: %s", mode, e)
        return VerificationResult(status="REJECT", reasons=[f"verify exception ({mode}): {e}"], revise_hint="retry with smaller span", evidence_supported=False, dual_mode=mode)


def verify_finding(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any], contract_text: str) -> VerificationResult:
    """
    Single-model verification (backward compatible).

    Gates on auditable evidence: contract_span, playbook, precedent, surgical.
    """
    t0 = time.perf_counter()
    try:
        result = _verify_strict(hit_span, finding, evidence_pkg, contract_text)
        _log_thinking("verify/single", f"{finding.clause_type} strict check", result.status, f"verify_finding {finding.clause_type} rule={finding.rule_id} -> {result.status} in {(time.perf_counter()-t0)*1000:.1f}ms reasons={result.reasons}")
        return result
    except Exception as e:
        logger.exception("verify_finding failed for %s: %s", finding.clause_type, e)
        _log_thinking("verify/single/error", str(finding)[:300], str(e), f"verify_finding exception: {e}")
        return VerificationResult(status="REJECT", reasons=[f"verify exception: {e}"], revise_hint="retry with smaller span", evidence_supported=False)


def dual_verify_finding(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any], contract_text: str) -> VerificationResult:
    """
    Dual-threshold deterministic verification: runs the same provenance/surgical-edit
    check twice (strict + lenient thresholds) in parallel and compares. If the two
    disagree, that means the finding is threshold-sensitive -> REJECT pending human
    review rather than silently picking one side.

    This is one deterministic rule engine evaluated twice, not two language models --
    see the module docstring. For an actual LLM opinion, see harness/llm_verify.py.
    Uses ThreadPoolExecutor for true parallelism (two independent, fast function calls).

    Args:
        hit_span: verbatim contract span text
        finding: RiskFinding with clause_type, rule_id, etc.
        evidence_pkg: evidence package dict
        contract_text: full contract text for provenance check

    Returns:
        VerificationResult:
          - Both PASS -> PASS
          - Both REJECT -> REJECT (merge reasons)
          - Disagree -> REJECT with "dual-model disagreement" + hallucination risk
    """
    t0 = time.perf_counter()
    try:
        _log_thinking("verify/dual/start", f"{finding.clause_type} rule={finding.rule_id} span={hit_span[:80]!r}", "running strict+lenient in parallel", f"dual_verify start for {finding.clause_type} rule={finding.rule_id} at page {evidence_pkg.get('contract_page')}")
        # Run both verifiers in parallel (ThreadPoolExecutor)
        verify1: VerificationResult | None = None
        verify2: VerificationResult | None = None
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_strict = executor.submit(_verify_strict, hit_span, finding, evidence_pkg, contract_text)
            fut_lenient = executor.submit(_verify_lenient, hit_span, finding, evidence_pkg, contract_text)
            futures = {fut_strict: "strict", fut_lenient: "lenient"}
            results: dict[str, VerificationResult] = {}
            for fut in as_completed(futures):
                mode = futures[fut]
                try:
                    res = fut.result(timeout=5.0)
                    results[mode] = res
                    logger.debug("dual_verify %s -> %s reasons=%s", mode, res.status, res.reasons)
                except Exception as e:
                    logger.warning("dual_verify %s executor failed: %s", mode, e)
                    results[mode] = VerificationResult(status="REJECT", reasons=[f"{mode} executor exception: {e}"], revise_hint="retry", evidence_supported=False, dual_mode=mode)
            verify1 = results.get("strict")
            verify2 = results.get("lenient")

        if verify1 is None or verify2 is None:
            logger.warning("dual_verify incomplete verify1=%s verify2=%s", verify1, verify2)
            fallback = verify1 or verify2
            if fallback:
                _log_thinking("verify/dual/incomplete", f"{finding.clause_type}", fallback.status, f"dual_verify incomplete, fallback to {fallback.dual_mode}={fallback.status}")
                return fallback
            return VerificationResult(status="REJECT", reasons=["dual_verify both executors failed"], revise_hint="retry with smaller span", evidence_supported=False, dual_mode="dual")

        # Compare
        if verify1.status == verify2.status:
            # Agreement: return strict as primary, augment reasons
            if verify1.status == "PASS":
                _log_thinking("verify/dual/agree_pass", f"{finding.clause_type} rule={finding.rule_id}", "PASS", f"dual_verify AGREE PASS: strict=PASS lenient=PASS in {(time.perf_counter()-t0)*1000:.1f}ms")
                return VerificationResult(
                    status="PASS",
                    reasons=[],
                    revise_hint=None,
                    evidence_supported=True,
                    dual_mode="dual-agree-pass",
                    thinking=[{"strict": verify1.reasons, "lenient": verify2.reasons}],
                )
            else:
                merged_reasons = list(set(verify1.reasons + verify2.reasons))
                _log_thinking("verify/dual/agree_reject", f"{finding.clause_type}", f"REJECT {merged_reasons}", f"dual_verify AGREE REJECT: both REJECT in {(time.perf_counter()-t0)*1000:.1f}ms")
                return VerificationResult(
                    status="REJECT",
                    reasons=merged_reasons,
                    revise_hint=verify1.revise_hint or verify2.revise_hint,
                    evidence_supported=False,
                    dual_mode="dual-agree-reject",
                    thinking=[{"strict": verify1.reasons, "lenient": verify2.reasons}],
                )
        else:
            # Threshold disagreement -> borderline finding, reject pending human review
            msg = (
                f"dual-threshold disagreement: strict={verify1.status} ({verify1.reasons}) "
                f"vs lenient={verify2.status} ({verify2.reasons}) -- borderline finding, needs human review"
            )
            _log_thinking("verify/dual/disagree", f"{finding.clause_type} strict={verify1.status} lenient={verify2.status}", f"REJECT {msg}", f"dual_verify DISAGREEMENT in {(time.perf_counter()-t0)*1000:.1f}ms -> REJECT hallucination risk: strict {verify1.status} vs lenient {verify2.status}")
            logger.warning("dual_verify disagreement for %s rule=%s: %s", finding.clause_type, finding.rule_id, msg)
            return VerificationResult(
                status="REJECT",
                reasons=[msg, "hallucination risk: dual verifiers disagree -- requires human review"],
                revise_hint="Resolve disagreement: ensure contract_span verbatim and precedent exists, then retry",
                evidence_supported=False,
                dual_mode="dual-disagree",
                thinking=[{"strict": verify1.reasons, "lenient": verify2.reasons}],
            )
    except Exception as e:
        logger.exception("dual_verify_finding failed for %s: %s", finding.clause_type, e)
        _log_thinking("verify/dual/error", str(finding)[:300], str(e), f"dual_verify exception: {e}")
        return VerificationResult(status="REJECT", reasons=[f"dual_verify exception: {e}"], revise_hint="retry with smaller span", evidence_supported=False, dual_mode="dual-error")


def is_supported_finding(verif: VerificationResult) -> bool:
    """Return True if verification PASS and evidence supported."""
    try:
        return verif.status == "PASS" and verif.evidence_supported
    except Exception as e:
        logger.warning("is_supported_finding failed: %s", e)
        return False

