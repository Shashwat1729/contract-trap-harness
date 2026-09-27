"""
Risk -- playbook + precedent retrieval with evidence package.

Playbook is 12 SaaS rules (P-01..P-12) grounded in CUAD handbook + RedlineBench commerce context.
Precedent store is tiny in fixtures (Acme, LargeCo, GiantCo) -- production BM25-style via rapidfuzz, no heavy index needed.

Upgraded to Best Overall (Apollo-style self-reflective RAG):
- self_reflective_retrieve(query, trap_id) iteratively retrieves with coverage check
- Thinking logs per RiskWise Developer View (timestamp, input, output, reasoning)
- Persistent evidence/reviews/thinking_*.json

Production-grade: type hints, docstrings, logging, try/except per function.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .extract import ClauseHit, find_duration, find_durations

logger = logging.getLogger("advanced.harness.risk")

# ---------------------------------------------------------------------------
# Thinking log (RiskWise Developer View)
# ---------------------------------------------------------------------------
THINKING_LOG: list[dict[str, Any]] = []
_THINKING_MAX = 500


def _log_thinking(stage: str, input_data: Any, output_data: Any, reasoning: str) -> None:
    """Append a thinking entry with timestamp. Never raises."""
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
        # Persist to file (best-effort, no raise)
        try:
            evidence_dir = Path(__file__).parents[2] / "evidence" / "reviews"
            # also handle advanced/src/harness -> advanced/evidence/reviews
            alt_dir = Path(__file__).parents[1].parent / "evidence" / "reviews"
            for d in (evidence_dir, alt_dir):
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    fp = d / "thinking_risk.json"
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
    """Return recent thinking entries (in-memory)."""
    try:
        return THINKING_LOG[-limit:]
    except Exception as e:
        logger.warning("get_thinking_log failed: %s", e)
        return []


def save_thinking_log(path: str | Path | None = None) -> Path | None:
    """Persist full thinking log to evidence/reviews/thinking_risk_*.json."""
    try:
        p = Path(path) if path else Path(__file__).parents[2] / "evidence" / "reviews" / f"thinking_risk_{int(time.time())}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(THINKING_LOG, f, indent=2, ensure_ascii=False)
        logger.info("thinking log saved to %s (%d entries)", p, len(THINKING_LOG))
        return p
    except Exception as e:
        logger.exception("save_thinking_log failed: %s", e)
        return None

# ---------------------------------------------------------------------------
# Production playbook -- each rule defines what constitutes a trap and preferred language
# ---------------------------------------------------------------------------
PLAYBOOK: dict[str, dict[str, Any]] = {
    "P-01": {"clause_types": ["Renewal Term"], "trap": "renewal >12 months", "preferred": "Initial Term 12 months, renewal Term 12 months.", "commercial": "Pilot must not lock in; 12m is market.", "precedent": "Acme MSA 2024-03 S8.2"},
    "P-02": {"clause_types": ["Notice Period to Terminate Renewal"], "trap": "notice period <60 days is too short to act before auto-renewal locks in (independent of the renewal term length itself)", "preferred": "90 days notice prior to renewal.", "commercial": "Ops needs 90 days to evaluate alternatives.", "precedent": "Acme MSA 2024-03 S8.3"},
    "P-03": {"clause_types": ["Termination for Convenience"], "trap": "missing TFC", "preferred": "Either party may terminate for convenience on 30 days notice.", "commercial": "TalentFlow is pilot, needs exit.", "precedent": "LargeCo Template S12.1"},
    "P-04": {"clause_types": ["Cap on Liability", "Limitation of Liability"], "trap": "uncapped / unlimited", "preferred": "Liability capped at fees paid in 12 months preceding claim.", "commercial": "Series A cannot bear uncapped.", "precedent": "GiantCo Services S9.4"},
    "P-05": {"clause_types": ["Audit Rights"], "trap": "unlimited audits / any time without notice", "preferred": "One audit per year on 30 days notice.", "commercial": "Ops burden for pilot.", "precedent": "AgentCo Playbook PR-08"},
    "P-06": {"clause_types": ["Governing Law"], "trap": "vendor-favorable jurisdiction without mutuality", "preferred": "Delaware, mutual.", "commercial": "AgentCo is Delaware C-Corp.", "precedent": "LargeCo MSA S14.1"},
    "P-07": {"clause_types": ["License Grant"], "trap": "irrevocable/perpetual without termination linkage", "preferred": "License terminates on termination.", "commercial": "No perpetual after exit.", "precedent": "AgentCo MSA S3.1"},
    "P-08": {"clause_types": ["Non-Compete"], "trap": "broad non-compete >12 months / non-market", "preferred": "Narrow to direct competitors, 6 months.", "commercial": "TalentFlow is HR tech, broad non-compete blocks GTM.", "precedent": "AgentCo Playbook PR-11"},
    "P-09": {"clause_types": ["Non-Disparagement"], "trap": "one-way disparagement only", "preferred": "Mutual non-disparagement.", "commercial": "Mutuality for enterprise deal.", "precedent": "LargeCo S11.4"},
    "P-10": {"clause_types": ["IP Ownership Assignment"], "trap": "vendor owns customer data/IP", "preferred": "Customer retains IP, vendor retains platform IP.", "commercial": "TalentFlow is core HR data.", "precedent": "AgentCo Playbook PR-02"},
    "P-11": {"clause_types": ["Post-Termination Services"], "trap": "no transition assistance / conflicting retention", "preferred": "30 days transition at prior rates.", "commercial": "Need offboarding window.", "precedent": "GiantCo S7.3"},
    "P-12": {"clause_types": ["Cap on Liability", "Limitation of Liability"], "trap": "carve-outs bypass cap (e.g., excluded from cap)", "preferred": "Carve-outs limited to fraud/willful misconduct.", "commercial": "Carve-outs that bypass cap defeat purpose.", "precedent": "Acme S9.5"},
}

# In-memory precedent corpus (tiny, production would be vector DB; deterministic + reproducible)
PRECEDENTS = [
    {"id": "PR-01", "title": "Acme MSA 2024-03 S8.2 Renewal", "text": "Renewal Term 12 months, 90 days notice. Liability capped at 12 months fees."},
    {"id": "PR-02", "title": "LargeCo Template S12.1 TFC", "text": "Either party may terminate for convenience on 30 days written notice."},
    {"id": "PR-03", "title": "GiantCo Services S9.4 Liability", "text": "Liability cap = fees paid in 12 months preceding claim, carve-outs limited to fraud."},
    {"id": "PR-04", "title": "AgentCo Playbook PR-08 Audit", "text": "One audit per year on 30 days notice, during business hours."},
    {"id": "PR-08", "title": "AgentCo Playbook PR-11 Non-Compete", "text": "Non-compete limited to direct competitors, 6 months, geography US."},
    {"id": "PR-09", "title": "Acme S9.5 Carve-out", "text": "Carve-outs from liability cap limited to fraud and willful misconduct."},
    {"id": "PR-10", "title": "AgentCo Playbook PR-02 IP", "text": "Customer retains ownership of customer data and IP, vendor retains platform IP."},
    {"id": "PR-05", "title": "LargeCo MSA S14.1 Governing Law", "text": "Governing law is the State of Delaware. Both parties consent to mutual jurisdiction with no unilateral forum selection favoring either side."},
    {"id": "PR-06", "title": "LargeCo S11.4 Non-Disparagement", "text": "Non-disparagement obligations are mutual. Neither party will disparage the other, during the term or after termination."},
]

# Query broadening map (Apollo-style: narrow -> broad)
_BROADEN_MAP: dict[str, str] = {
    "renewal term trap": "renewal auto-renewal",
    "renewal term": "renewal auto-renewal term",
    "notice period trap": "notice termination renewal",
    "liability cap trap": "liability limitation cap",
    "cap on liability trap": "liability limitation unlimited",
    "audit rights trap": "audit inspection rights",
    "governing law trap": "jurisdiction governing law",
    "license grant trap": "license irrevocable perpetual",
    "non-compete trap": "non-compete covenant competition",
    "ip ownership trap": "intellectual property assignment ownership",
    "post-termination trap": "transition services termination",
}


def _broaden_query(query: str) -> str:
    """Broaden a narrow trap query for second-pass retrieval."""
    try:
        q_lower = query.strip().lower()
        if q_lower in _BROADEN_MAP:
            return _BROADEN_MAP[q_lower]
        for k, v in _BROADEN_MAP.items():
            if k in q_lower:
                return v
        # Generic broadening: remove "trap", expand synonyms
        broadened = query
        if " trap" in q_lower:
            broadened = broadened.lower().replace(" trap", "").strip()
        synonyms: dict[str, str] = {
            "renewal": "auto-renewal",
            "cap": "limitation",
            "termination": "convenience",
            "audit": "inspection",
        }
        for narrow, broad in synonyms.items():
            if narrow in q_lower and broad not in q_lower:
                broadened = f"{broadened} {broad}"
        return broadened.strip() or query
    except Exception as e:
        logger.warning("_broaden_query fallback for %r: %s", query, e)
        return query


def _check_coverage(
    precedent: list[dict[str, Any]] | None,
    playbook_entry: dict[str, Any] | None,
    contract_span: str | None = None,
) -> dict[str, bool]:
    """
    Check if we have enough evidence for a trap.

    Coverage requires:
    - contract_span: non-empty span text
    - playbook: rule exists for trap_id
    - precedent: at least one precedent retrieved with score > threshold
    """
    try:
        has_span = bool(contract_span and contract_span.strip())
        has_playbook = bool(playbook_entry)
        has_precedent = bool(precedent and len(precedent) > 0)
        return {
            "has_span": has_span,
            "has_playbook": has_playbook,
            "has_precedent": has_precedent,
            "complete": has_span and has_playbook and has_precedent,
        }
    except Exception as e:
        logger.warning("_check_coverage failed: %s", e)
        return {"has_span": False, "has_playbook": False, "has_precedent": False, "complete": False}


RENEWAL_KEYWORD = r"renew(?:s|al|als|ed|ing)?"
INITIAL_TERM_LEAD_IN = r"\binitial\b"


def _unit_name(unit: str) -> str:
    """Map the legacy regex-style unit argument ("months?", "days?") to find_durations' unit."""
    u = unit.lower()
    if u.startswith("month"):
        return "month"
    if u.startswith("day"):
        return "day"
    raise ValueError(f"unsupported unit {unit!r}")


def _find_number_before_unit(text: str, unit: str) -> int | None:
    """
    First duration in `unit` in text. Tolerates the extremely common legal-drafting
    convention of spelling the number out with the numeral in parentheses right after --
    "thirty-six (36) months", "ninety (90) days" -- as well as the bare-digit form
    ("36 months"), a spelled-out number alone ("ninety days"), and, for months, year
    durations ("two (2) years" -> 24). A unit word with no number attached ("monthly
    fees") is ignored rather than read as the preceding unrelated number.
    """
    return find_duration(text, _unit_name(unit))


def _find_number_near_keyword(text: str, keyword_pattern: str, unit: str, radius: int = 100, skip_if_preceded_by: str | None = None) -> int | None:
    """
    Like _find_number_before_unit, but prefers a number that appears shortly after an
    anchor keyword (e.g. "renew") over the first number-before-unit match in the whole
    span. A clause commonly states an unrelated number first -- "Initial Term of twelve
    (12) months" -- before the number that actually matters -- "renews for successive
    terms of thirty-six (36) months" -- and the plain first-match search silently picks
    up the safe Initial Term value instead of the actual Renewal Term value, missing a
    real trap. Falls back to the plain first-match search when no anchored match exists
    (single-number spans, or the anchor keyword isn't present).

    A duration whose lead-in (between the anchor keyword and the number) matches
    `skip_if_preceded_by` is skipped: e.g. a "Term and Renewal" section header followed by
    "...continues for an initial period of one year" must not be read as the renewal term.
    """
    uname = _unit_name(unit)
    for km in re.finditer(keyword_pattern, text, flags=re.IGNORECASE):
        window = text[km.end(): km.end() + radius]
        for offset, val in find_durations(window, uname):
            if skip_if_preceded_by and re.search(skip_if_preceded_by, window[:offset], flags=re.IGNORECASE):
                continue
            return val
    if skip_if_preceded_by:
        # No anchored match: take the first duration in the whole span that isn't
        # introduced as the excluded kind (e.g. the initial term), before falling back
        # to the plain first match.
        for offset, val in find_durations(text, uname):
            if not re.search(skip_if_preceded_by, text[max(0, offset - 80):offset], flags=re.IGNORECASE):
                return val
    return _find_number_before_unit(text, unit)


@dataclass
class RiskFinding:
    clause_type: str
    risk: str
    rule_id: str
    precedent_id: str
    proposed_change: str
    rationale: str
    confidence: float
    evidence_contract_span: str
    evidence_page: int
    evidence_line: int


def assess_risk(hit: ClauseHit) -> RiskFinding | None:
    """Map clause hit -> risk finding via playbook. Returns None if not risky."""
    t0 = time.perf_counter()
    try:
        for rid, rule in PLAYBOOK.items():
            if hit.clause_type in rule["clause_types"]:
                finding: RiskFinding | None = None
                if hit.clause_type == "Renewal Term":
                    months_val = _find_number_near_keyword(hit.span_text, RENEWAL_KEYWORD, "months?", skip_if_preceded_by=INITIAL_TERM_LEAD_IN)
                    if months_val is not None and months_val > 12:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.88, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (renewal <=12m)", f"Clause {hit.clause_type} at page {hit.page}:{hit.line} -- renewal term within safe 12m, no finding")
                        return None
                elif hit.clause_type == "Notice Period to Terminate Renewal":
                    days_val = _find_number_before_unit(hit.span_text, "days?")
                    if days_val is not None and days_val < 60:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.84, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (notice >=60d)", f"Notice period >=60d safe, no finding for {hit.clause_type}")
                        return None
                elif hit.clause_type in ("Cap on Liability", "Limitation of Liability"):
                    if re.search(r"carve-out|excluded from cap|not subject to limitation|bypass.*cap|shall not apply to|does not apply to|foregoing limitation.*shall not", hit.span_text, flags=re.IGNORECASE):
                        # Carve-out-bypass is P-12's trap, not P-04's "uncapped" -- using P-04's
                        # description here would tell a reviewer (or the LLM cross-check) the
                        # contract is "uncapped" when it is actually capped-but-bypassed, which
                        # is a different, misleading claim. Attribute to the rule that actually
                        # matches the condition found.
                        p12 = PLAYBOOK["P-12"]
                        finding = RiskFinding(clause_type=hit.clause_type, risk="High", rule_id="P-12", precedent_id=p12["precedent"].split()[0], proposed_change=p12["preferred"], rationale=p12["commercial"] + " " + p12["trap"], confidence=0.91, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    elif re.search(r"uncapped|unlimited", hit.span_text, flags=re.IGNORECASE):
                        finding = RiskFinding(clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.91, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                elif hit.clause_type == "License Grant":
                    trap_kws = ["irrevocable", "perpetual", "unlimited", "without limitation"]
                    if any(re.search(kw, hit.span_text, flags=re.IGNORECASE) for kw in trap_kws):
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.76, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap keyword", f"{hit.clause_type} -- no trap keywords matched, safe")
                        return None
                elif hit.clause_type == "IP Ownership Assignment":
                    # Trap: vendor claims ownership of what CUSTOMER creates/submits -- NOT
                    # simply "vendor owns X" (vendor legitimately owning its own platform/
                    # source code/IP is the normal, safe state). The "vendor owns ..." form
                    # only counts as a trap when the object is customer-side content.
                    trap = bool(re.search(r"\bowns?\b.{0,20}customer|owned\s+(?:exclusively\s+|solely\s+)?by\s+vendor", hit.span_text, flags=re.IGNORECASE))
                    if not trap:
                        vendor_owns = re.search(r"vendor\s+(?:shall\s+|will\s+)?(?:owns?|retains?\s+ownership\s+of|is\s+the\s+(?:sole|exclusive)\s+owner\s+of)\s+(?:all\s+|any\s+)?(customer|data|content|material|work\s+product)", hit.span_text, flags=re.IGNORECASE)
                        trap = bool(vendor_owns)
                    if trap:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.76, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (vendor owns own IP, not customer's)", f"{hit.clause_type} -- ownership language refers to vendor's own IP, not customer content, safe")
                        return None
                elif hit.clause_type == "Non-Compete":
                    # A Non-Compete header alone isn't a trap -- the trap is overreach (broad
                    # scope or long duration). Checking for the bare word "non-compete" here
                    # would trivially match every non-compete clause via its own header, safe
                    # or not, so check the actual overreach signals instead.
                    months_val = _find_number_before_unit(hit.span_text, "months?")
                    duration_over = months_val is not None and months_val > 12
                    broad_scope = re.search(r"worldwide|anywhere|any\s+business|any\s+entity|global(?:ly)?", hit.span_text, flags=re.IGNORECASE)
                    if duration_over or broad_scope:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.76, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (non-compete narrow/short)", "Non-Compete clause is scoped and <=12mo, no finding")
                        return None
                elif hit.clause_type == "Post-Termination Services":
                    # P-11's trap is "no transition assistance / conflicting retention" -- checked
                    # directly against deletion/retention language, independent of the License/
                    # Non-Compete/IP keyword set above (which targets a different clause family).
                    has_delete = re.search(r"delet|eras|purg|destroy", hit.span_text, flags=re.IGNORECASE)
                    # Note: deliberately excludes bare "transition" -- "transition assistance/
                    # services" is the GOOD, expected thing, not the retention conflict; only
                    # actual retain-a-copy language counts as the conflicting-retention signal.
                    # A negated form ("no further retention", "without retaining a copy") means
                    # the opposite of the trap, so it must not count as has_retain either.
                    has_retain = re.search(r"retain|retention|keep a copy|continue to (?:hold|store)", hit.span_text, flags=re.IGNORECASE)
                    if has_retain and re.search(r"(?:no|not|without)\s+(?:further\s+)?" + re.escape(has_retain.group(0)), hit.span_text, flags=re.IGNORECASE):
                        has_retain = None
                    has_transition_assist = re.search(
                        r"transition\s+(?:assistance|services|support)|assist.{0,30}transition"
                        r"|available\s+for\s+export|export.{0,20}(?:data|content)|provide.{0,20}access"
                        r"|make.{0,30}available",
                        hit.span_text, flags=re.IGNORECASE,
                    )
                    if has_delete and has_retain:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.76, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    elif not has_transition_assist and not has_retain:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.68, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (transition covered, no conflict)", "Post-Termination Services clause has transition assistance with no delete/retain conflict, no finding")
                        return None
                elif hit.clause_type == "Audit Rights":
                    # Trap: no frequency/notice limit on audits ("at any time" / "without notice"),
                    # not offset by an explicit annual-cadence or notice-period carve-out.
                    unlimited = re.search(r"at any time|without (?:prior )?notice|unlimited\s+audit", hit.span_text, flags=re.IGNORECASE)
                    limited = re.search(r"once\s+(?:per|a)\s+year|annual(?:ly)?|(?:one|a)\s+audit\s+per\s+year|\(?\s*\d+\s*\)?\s*days?[\s\w]{0,15}notice", hit.span_text, flags=re.IGNORECASE)
                    if unlimited and not limited:
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.74, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (audit rights bounded)", "Audit Rights clause has a frequency/notice limit, no finding")
                        return None
                elif hit.clause_type == "Non-Disparagement":
                    # Trap: clause binds only one side, not both ("mutual"/"either party"/"both parties").
                    if not re.search(r"mutual|either\s+party|both\s+parties|neither\s+party", hit.span_text, flags=re.IGNORECASE):
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.7, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        _log_thinking("risk/assess", hit.span_text[:200], "no trap (already mutual)", "Non-Disparagement clause already mutual, no finding")
                        return None
                elif hit.clause_type == "Governing Law":
                    # Trap: any jurisdiction other than the client's home state (Delaware), not just
                    # California/New York -- the earlier CA/NY-only check missed every other state.
                    if not re.search(r"Delaware", hit.span_text, flags=re.IGNORECASE):
                        finding = RiskFinding(clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0], proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"], confidence=0.72, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line)
                    else:
                        return None
                if finding is not None:
                    _log_thinking(
                        "risk/assess",
                        f"{hit.clause_type} | {hit.span_text[:180]}",
                        f"RiskFinding {finding.rule_id} risk={finding.risk} conf={finding.confidence}",
                        f"Matched playbook {rid} for {hit.clause_type}: trap={rule['trap']}, proposed={rule['preferred'][:80]}, confidence {finding.confidence}, latency {(time.perf_counter()-t0)*1000:.1f}ms",
                    )
                    return finding
        _log_thinking("risk/assess", f"{hit.clause_type} | {hit.span_text[:180]}", "no rule matched", f"No playbook rule triggered for {hit.clause_type}, considered safe")
        return None
    except Exception as e:
        logger.exception("assess_risk failed for %s: %s", hit.clause_type, e)
        _log_thinking("risk/assess", str(hit)[:300], f"exception: {e}", f"assess_risk exception for {hit.clause_type}: {e}")
        return None


def retrieve_precedent(query_text: str, top_k: int = 1) -> list[dict[str, Any]]:
    """BM25-like via rapidfuzz token_set_ratio, deterministic, no heavy index."""
    try:
        result = _cached_retrieve(query_text, top_k)
        _log_thinking("risk/retrieve", query_text[:300], f"{len(result)} precedents", f"retrieve_precedent query={query_text[:80]!r} top_k={top_k} -> {[p['id'] for p in result]}")
        return result
    except Exception as e:
        logger.exception("retrieve_precedent failed for %r: %s", query_text[:80], e)
        _log_thinking("risk/retrieve", query_text[:200], f"error: {e}", f"retrieve failed: {e}")
        return []


@lru_cache(maxsize=128)
def _cached_retrieve(query_text: str, top_k: int = 1) -> list[dict[str, Any]]:
    scored = []
    for p in PRECEDENTS:
        score = fuzz.token_set_ratio(query_text.lower(), p["text"].lower())
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    result = [p for s, p in scored[:top_k] if s > 45]
    logger.debug("retrieve_precedent cache hit for %s -> %s", query_text[:40], len(result))
    return result


def self_reflective_retrieve(query: str, trap_id: str | None = None, max_iterations: int = 2, contract_span: str | None = None) -> dict[str, Any]:
    """
    Apollo-style self-reflective RAG: iteratively retrieve until coverage complete.

    Steps:
      1. Initial retrieve with narrow query
      2. Check coverage (contract_span + playbook + precedent)
      3. If gap, broaden query ("renewal term trap" -> "renewal auto-renewal") and retrieve again
      4. Repeat until coverage complete or max_iterations reached
      5. Log thinking at each step

    Args:
        query: initial narrow query, e.g. "renewal term trap"
        trap_id: optional playbook rule id (P-01..P-12) to check playbook coverage
        max_iterations: max retrieval rounds (default 2 per spec)
        contract_span: the actual clause text the caller has evidence for -- checked for
            real presence in coverage's has_span. If omitted, falls back to treating a
            non-empty query as span-present (a proxy, not a real span check -- only used
            when no caller-supplied span is available).

    Returns:
        dict with keys: query, iterations, precedent, playbook, coverage, thinking, all_results
    """
    thinking_steps: list[dict[str, Any]] = []
    all_results: list[list[dict[str, Any]]] = []
    start_ts = datetime.now(timezone.utc).isoformat()
    try:
        logger.info("self_reflective_retrieve start query=%r trap_id=%s max_iter=%d", query[:80], trap_id, max_iterations)
        playbook_entry: dict[str, Any] | None = PLAYBOOK.get(trap_id) if trap_id else None
        # If trap_id not provided but query maps to a clause, try to infer
        if not playbook_entry and trap_id:
            logger.warning("trap_id %s not in PLAYBOOK", trap_id)
        # For coverage span, we use query as proxy for contract_span presence (non-empty query implies need)
        current_query = query
        best_precedent: list[dict[str, Any]] = []
        coverage: dict[str, bool] = {}
        iterations = 0

        for i in range(max_iterations):
            iterations = i + 1
            step_input = {"iteration": iterations, "query": current_query, "trap_id": trap_id}
            # Retrieve
            try:
                results = _cached_retrieve(current_query, top_k=2)
                all_results.append(results)
                if results and (not best_precedent or len(results) > len(best_precedent)):
                    best_precedent = results
                logger.info("  iter %d query=%r -> %d hits %s", iterations, current_query[:60], len(results), [p["id"] for p in results])
            except Exception as e:
                logger.warning("  iter %d retrieve failed: %s", iterations, e)
                results = []
                all_results.append(results)

            # Check coverage: need playbook + precedent + span. Use the caller's real
            # contract span when supplied; only fall back to the query-non-empty proxy
            # when no span was given (e.g. exploratory calls with no matched clause yet).
            effective_span = contract_span if contract_span is not None else current_query
            coverage = _check_coverage(best_precedent, playbook_entry, effective_span)
            reasoning = (
                f"Iteration {iterations}/{max_iterations}: query={current_query!r} -> {len(results)} precedents, "
                f"coverage={{span:{coverage['has_span']}, playbook:{coverage['has_playbook']}, precedent:{coverage['has_precedent']}}} "
                f"complete={coverage['complete']}"
            )
            step_output = {"results": [p["id"] for p in results], "coverage": coverage}
            thinking_steps.append({"iteration": iterations, "query": current_query, "coverage": coverage, "reasoning": reasoning})
            _log_thinking("risk/self_reflective", step_input, step_output, reasoning)

            if coverage["complete"]:
                logger.info("self_reflective_retrieve coverage complete after %d iterations", iterations)
                break

            # If not complete and we have more iterations, broaden query
            if iterations < max_iterations:
                broadened = _broaden_query(current_query)
                if broadened == current_query:
                    # Already broad, try alternate broadening: take trap clause types
                    if playbook_entry:
                        broadened = " ".join(playbook_entry.get("clause_types", [])) + " " + broadened
                        broadened = broadened.strip()
                    else:
                        broadened = current_query + " contract provision"
                reasoning2 = f"Coverage gap detected (missing: {[k for k,v in coverage.items() if k!='complete' and not v]}), broadening query {current_query!r} -> {broadened!r} for next iteration"
                _log_thinking("risk/self_reflective/broaden", current_query, broadened, reasoning2)
                logger.info("  broadening: %r -> %r", current_query, broadened)
                current_query = broadened
            else:
                logger.info("self_reflective_retrieve max iterations reached, final coverage %s", coverage)

        output: dict[str, Any] = {
            "original_query": query,
            "final_query": current_query,
            "trap_id": trap_id,
            "iterations": iterations,
            "precedent": best_precedent[0] if best_precedent else None,
            "precedents": best_precedent,
            "all_results": all_results,
            "playbook": playbook_entry,
            "coverage": coverage,
            "coverage_complete": coverage.get("complete", False) if coverage else False,
            "thinking": thinking_steps,
            "started_at": start_ts,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        _log_thinking("risk/self_reflective/done", query, f"coverage_complete={output['coverage_complete']} iters={iterations}", f"Self-reflective RAG done: {query!r} trap={trap_id} -> complete={output['coverage_complete']} after {iterations} iters, precedent={output['precedent']['id'] if output['precedent'] else None}")
        return output
    except Exception as e:
        logger.exception("self_reflective_retrieve failed for %r trap=%s: %s", query[:80], trap_id, e)
        _log_thinking("risk/self_reflective/error", query, str(e), f"self_reflective_retrieve exception: {e}")
        return {
            "original_query": query,
            "final_query": query,
            "trap_id": trap_id,
            "iterations": 1,
            "precedent": None,
            "precedents": [],
            "all_results": all_results,
            "playbook": PLAYBOOK.get(trap_id) if trap_id else None,
            "coverage": {"has_span": False, "has_playbook": False, "has_precedent": False, "complete": False},
            "coverage_complete": False,
            "thinking": thinking_steps,
            "error": str(e),
        }


def build_evidence_package(hit: ClauseHit, finding: RiskFinding, contract_text: str, max_iterations: int = 2) -> dict[str, Any]:
    """Evidence package that verifier will gate on. Uses self-reflective retrieval.

    max_iterations is exposed (default 2) so a caller doing genuine revision after a
    REJECT (see harness/graph.py's revise_node) can retry with a deeper search (e.g. 3-4
    iterations) instead of silently repeating the identical retrieval that already failed.
    """
    try:
        # Use self-reflective retrieval for richer precedent (Apollo pattern)
        trap_query = f"{hit.clause_type} trap"
        reflect = self_reflective_retrieve(trap_query, trap_id=finding.rule_id, max_iterations=max_iterations, contract_span=hit.span_text)
        precedent = reflect.get("precedent")
        if not precedent:
            # Fallback to direct retrieve
            fallback = retrieve_precedent(finding.proposed_change)
            precedent = fallback[0] if fallback else None
        # Also try direct precedent by finding rule precedent id
        if not precedent:
            for p in PRECEDENTS:
                if p["id"] in finding.precedent_id or finding.precedent_id in p["id"]:
                    precedent = p
                    break

        pkg = {
            "contract_span": finding.evidence_contract_span,
            "contract_page": finding.evidence_page,
            "contract_line": finding.evidence_line,
            "contract_exists": finding.evidence_contract_span.strip()[:80] in contract_text if finding.evidence_contract_span else False,
            "playbook_rule": finding.rule_id,
            "playbook_text": PLAYBOOK[finding.rule_id]["trap"] + " -> " + PLAYBOOK[finding.rule_id]["preferred"],
            "commercial_instruction": PLAYBOOK[finding.rule_id]["commercial"],
            "precedent": precedent,
            "confidence": finding.confidence,
            "self_reflective": {"iterations": reflect.get("iterations"), "coverage_complete": reflect.get("coverage_complete"), "final_query": reflect.get("final_query")},
        }
        _log_thinking("risk/evidence_package", f"{hit.clause_type} rule={finding.rule_id}", f"precedent={precedent['id'] if precedent else None} coverage_complete={reflect.get('coverage_complete')}", f"Built evidence package for {hit.clause_type} at page {hit.page}:{hit.line}, precedent {precedent['id'] if precedent else 'none'}, self-reflective iters {reflect.get('iterations')}")
        return pkg
    except Exception as e:
        logger.exception("build_evidence_package failed for %s: %s", hit.clause_type, e)
        _log_thinking("risk/evidence_package", str(hit)[:200], f"error: {e}", f"evidence package failed: {e}")
        # Minimal fallback package
        return {
            "contract_span": finding.evidence_contract_span,
            "contract_page": finding.evidence_page,
            "contract_line": finding.evidence_line,
            "contract_exists": False,
            "playbook_rule": finding.rule_id,
            "playbook_text": PLAYBOOK.get(finding.rule_id, {}).get("trap", ""),
            "commercial_instruction": PLAYBOOK.get(finding.rule_id, {}).get("commercial", ""),
            "precedent": None,
            "confidence": finding.confidence,
            "self_reflective": {"iterations": 0, "coverage_complete": False, "error": str(e)},
        }

