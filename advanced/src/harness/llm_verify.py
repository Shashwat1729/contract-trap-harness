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
from typing import Any

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
    """Build user prompt with per-field isolation -- never crashes harness."""
    try:
        span = str(hit_span)[:800] if hit_span else ""
    except Exception as e:
        import logging as _lg
        _lg.getLogger("advanced.harness.llm_verify").warning("_build_llm_prompt span failed: %s", e)
        span = ""
    try:
        rule = str(evidence_pkg.get("playbook_text", ""))[:400] if evidence_pkg else ""
    except Exception as e:
        import logging as _lg2
        _lg2.getLogger("advanced.harness.llm_verify").warning("_build_llm_prompt rule failed: %s", e)
        rule = ""
    try:
        change = str(finding.proposed_change)[:300] if finding and hasattr(finding, "proposed_change") else ""
        rationale = str(finding.rationale)[:300] if finding and hasattr(finding, "rationale") else ""
        clause = str(finding.clause_type) if finding and hasattr(finding, "clause_type") else ""
        page = str(finding.evidence_page) if finding and hasattr(finding, "evidence_page") else "?"
        line = str(finding.evidence_line) if finding and hasattr(finding, "evidence_line") else "?"
    except Exception as e:
        import logging as _lg3
        _lg3.getLogger("advanced.harness.llm_verify").warning("_build_llm_prompt finding fields failed: %s", e)
        change = rationale = clause = page = line = ""
    try:
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
    except Exception as e:
        import logging as _lg4
        _lg4.getLogger("advanced.harness.llm_verify").warning("_build_llm_prompt final assembly failed: %s", e)
        return f"Contract span: {span[:500]}\nDoes this support the finding? Reply JSON only."

def llm_verify_finding(hit_span: str, finding: RiskFinding, evidence_pkg: dict[str, Any]) -> LLMVerifyResult:
    """Ask the LLM whether hit_span genuinely supports finding. Never raises. Per-helper isolation + timeout via llm.py (25s)."""
    try:
        if not llm_available():
            return LLMVerifyResult(ran=False, supported=None, confidence=None, concern="", mock=True)
    except Exception as e:
        import logging as _lg
        _lg.getLogger("advanced.harness.llm_verify").warning("llm_available check failed: %s", e)
        return LLMVerifyResult(ran=False, supported=None, confidence=None, concern="", mock=True, error=str(e))

    user = (
        f"Playbook rule under review: {evidence_pkg.get('playbook_text', '')}\n"
        f"This rule applies ONLY to clause type: {finding.clause_type}. If the span below also "
        "contains other, unrelated provisions, ignore them -- judge only whether THIS rule, for "
        "THIS clause type, is genuinely triggered.\n\n"
        f"Contract span (verbatim, cited at page {finding.evidence_page} line {finding.evidence_line}):\n"
        f"\"\"\"\n{hit_span[:800]}\n\"\"\"\n\n"
        f"Proposed change: {finding.proposed_change}\n"
        f"Rationale given: {finding.rationale}\n\n"
        "Does the span genuinely trigger this specific rule for this specific clause type? "
        "Respond with the JSON object only."
    )
    mock = {"supported": True, "confidence": round(finding.confidence, 2), "concern": ""}
    # Generous max_tokens: some providers (e.g. Gemini 2.5 "thinking" models) spend part of
    # the output budget on internal reasoning before the visible JSON reply -- too tight a
    # cap truncates the reply mid-object and makes a genuinely successful call look failed.
    result = call_llm_json(SYSTEM_PROMPT, user, max_tokens=1000, mock_response=mock)

    try:
        return LLMVerifyResult(
            ran=bool(result.get("_ran", False)),
            supported=bool(result.get("supported", True)),
            confidence=float(result.get("confidence", 0.5)),
            concern=str(result.get("concern", "") or "")[:300],
            mock=bool(result.get("_mock", True)),
            error=result.get("_error"),
        )
    except (TypeError, ValueError) as e:
        logger.warning("llm_verify_finding: malformed LLM JSON, treating as inconclusive: %s", e)
        return LLMVerifyResult(ran=True, supported=None, confidence=None, concern="", mock=True, error=str(e))
