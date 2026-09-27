"""
LLM verification -- a genuine second opinion from a real language model, run
alongside the deterministic dual-threshold verifier in verify.py.

Important distinction (see verify.py docstring): verify.dual_verify_finding runs
the SAME deterministic regex/fuzzy-match function twice at two thresholds -- a
legitimate ensemble technique, but not two language models, despite the historical
"dual-LM" naming. This module is the actual LLM call: it hands the proposed
finding + its evidence span to LLM_MODEL and asks it to judge, in its own words,
whether the evidence supports the claim.

Gated by ENABLE_LLM_VERIFY + llm.llm_available(): with no API key, or EVAL_MOCK=1,
or the flag off, this degrades to a no-op (ran=False) and the harness falls back to
the deterministic gate alone -- reproducibility for judges without a key is preserved.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from .llm import call_llm_json, llm_available
from .risk import RiskFinding

logger = logging.getLogger("advanced.harness.llm_verify")

SYSTEM_PROMPT = (
    "You are a strict, skeptical contract-review verifier. You are given a proposed "
    "redline finding plus the contract text it was extracted from. Judge ONLY whether "
    "the cited span genuinely supports the finding -- flag hallucinated citations, "
    "clause-type mismatches, or overstated risk. Do not be persuaded by confident "
    "phrasing. Reply with ONLY a single JSON object, no prose, no markdown fence, and "
    'keep "concern" under 12 words:\n'
    '{"supported": true|false, "confidence": <0.0-1.0>, "concern": "<12 words max, or empty string>"}'
)


@dataclass
class LLMVerifyResult:
    ran: bool
    supported: bool | None
    confidence: float | None
    concern: str
    mock: bool
    error: str | None = None


def _build_llm_prompt(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any]) -> str:
    """Build the user prompt; tolerant of missing finding fields."""
    span = str(hit_span or "")[:800]
    rule = str((evidence_pkg or {}).get("playbook_text", ""))[:400]
    change = str(getattr(finding, "proposed_change", ""))[:300]
    rationale = str(getattr(finding, "rationale", ""))[:300]
    clause = str(getattr(finding, "clause_type", ""))
    page = str(getattr(finding, "evidence_page", "?"))
    line = str(getattr(finding, "evidence_line", "?"))
    return (
        f"Playbook rule under review: {rule}\n"
        f"This rule applies ONLY to clause type: {clause}. If the span below also "
        "contains other, unrelated provisions, ignore them -- judge only whether THIS rule, for "
        "THIS clause type, is genuinely triggered.\n\n"
        f"Contract span (verbatim, cited at page {page} line {line}):\n"
        f"\"\"\"\n{span}\n\"\"\"\n\n"
        f"Proposed change: {change}\n"
        f"Rationale given: {rationale}\n\n"
        "Does the span genuinely trigger this specific rule for this specific clause type? "
        "Respond with the JSON object only."
    )


def _parse_bool(value: Any) -> bool | None:
    """Strict tri-state boolean: JSON true/false, or the strings/ints models sometimes emit
    instead. Anything unrecognised is None (inconclusive) -- never truthiness, which read
    the string "false" as True and silently discarded the model's disagreement."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "supported", "1"):
            return True
        if v in ("false", "no", "unsupported", "0"):
            return False
    return None


def _parse_confidence(value: Any) -> float | None:
    """Float in [0, 1], accepting "0.8" and percentages like 80 / "80%"; else None."""
    try:
        if isinstance(value, str):
            value = value.strip().rstrip("%")
        conf = float(value)
    except (TypeError, ValueError):
        return None
    if conf != conf:  # NaN
        return None
    if 1.0 < conf <= 100.0:
        conf /= 100.0
    return min(max(conf, 0.0), 1.0)


def llm_verify_finding(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any]) -> LLMVerifyResult:
    """Ask the LLM whether hit_span genuinely supports finding. Never raises. Per-helper isolation + timeout via llm.py."""
    try:
        if not llm_available():
            return LLMVerifyResult(ran=False, supported=None, confidence=None, concern="", mock=True)
    except Exception as e:
        logger.warning("llm_available check failed: %s", e)
        return LLMVerifyResult(ran=False, supported=None, confidence=None, concern="", mock=True, error=str(e))

    user = _build_llm_prompt(hit_span, finding, evidence_pkg)
    mock = {"supported": True, "confidence": round(finding.confidence, 2), "concern": ""}
    # Generous max_tokens: some providers (e.g. Gemini 2.5 "thinking" models) spend part of
    # the output budget on internal reasoning before the visible JSON reply -- too tight a
    # cap truncates the reply mid-object and makes a genuinely successful call look failed.
    result = call_llm_json(SYSTEM_PROMPT, user, max_tokens=1000, mock_response=mock)

    ran = bool(result.get("_ran", False))
    supported = _parse_bool(result.get("supported"))
    confidence = _parse_confidence(result.get("confidence"))
    if ran and supported is None:
        logger.warning("llm_verify_finding: unrecognised 'supported' value %r -- treating as inconclusive", result.get("supported"))
    return LLMVerifyResult(
        ran=ran,
        supported=supported,
        confidence=confidence,
        concern=str(result.get("concern", "") or "")[:300],
        mock=bool(result.get("_mock", True)),
        error=result.get("_error"),
    )


# A model verdict of "unsupported" at or above this confidence downgrades a PASS.
LLM_FLAG_MIN_CONFIDENCE = 0.6


def new_llm_stats() -> dict[str, int]:
    return {"ran": 0, "confirmed": 0, "flagged": 0, "inconclusive": 0, "skipped": 0, "mock": 0, "skipped_high_confidence": 0}


def llm_cross_check(
    hit_span: str,
    finding: RiskFinding,
    evidence_pkg: dict[str, Any],
    ver: Any,
    llm_stats: dict[str, int],
    *,
    enabled: bool,
    skip_confidence: float,
    verify_fn: Callable[..., LLMVerifyResult] | None = None,
) -> LLMVerifyResult | None:
    """
    The LLM cross-check stage shared by the direct pipeline (core.py) and the LangGraph
    verify node, so the two engines cannot drift apart. Mutates `ver` (PASS -> REJECT when
    the model flags the finding) and `llm_stats`; returns the LLM result, or None when no
    call was made.

    Only deterministic PASSes are checked. Confidence-based routing (CHANGELOG #20): the
    call is skipped when the dual verifier's strict+lenient thresholds already agreed PASS
    and the playbook rule's own confidence is >= skip_confidence.

    Verdicts: supported=False with confidence >= LLM_FLAG_MIN_CONFIDENCE (or no usable
    confidence at all -- an explicit "unsupported" is not waved through just because the
    model omitted a number) -> flagged. supported=None (unparseable) -> inconclusive, the
    deterministic verdict stands. Otherwise confirmed.
    """
    if not enabled or getattr(ver, "status", None) != "PASS":
        return None
    if getattr(ver, "dual_mode", None) == "dual-agree-pass" and finding.confidence >= skip_confidence:
        llm_stats["skipped_high_confidence"] += 1
        return None
    fn = verify_fn or llm_verify_finding
    try:
        res = fn(hit_span, finding, evidence_pkg)
    except Exception as e:
        logger.warning("llm_verify_finding failed for %s: %s", finding.clause_type, e)
        llm_stats["skipped"] += 1
        return None
    if not res.ran:
        llm_stats["skipped"] += 1
        return res
    llm_stats["ran"] += 1
    if res.mock:
        llm_stats["mock"] += 1
    if res.supported is False and (res.confidence is None or res.confidence >= LLM_FLAG_MIN_CONFIDENCE):
        llm_stats["flagged"] += 1
        ver.status = "REJECT"
        ver.reasons = list(ver.reasons) + [f"LLM cross-check flagged: {res.concern or 'unsupported per LLM review'}"]
        ver.evidence_supported = False
    elif res.supported is None:
        llm_stats["inconclusive"] += 1
    else:
        llm_stats["confirmed"] += 1
    return res


def llm_result_dict(res: LLMVerifyResult | None) -> dict[str, Any]:
    """Serializable per-finding view of the cross-check (same shape for both engines)."""
    if res is None:
        return {"ran": False, "supported": None, "confidence": None, "concern": "", "mock": True}
    return {"ran": res.ran, "supported": res.supported, "confidence": res.confidence, "concern": res.concern, "mock": res.mock}
