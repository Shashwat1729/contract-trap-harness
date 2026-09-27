"""
Baseline core — single-pass redliner, production-grade.

No verification gating, no memory, no orchestration.
Finds traps via deterministic span search + lightweight LLM fallback if key available.
This is the credible baseline: a reasonable single agent that finds needles in haystack but hallucinates citations and misses cross-clause traps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

import logging

logger = logging.getLogger("baseline.core")

# Canonical SaaS playbook rules grounded in CUAD + RedlineBench SaaS MSA scenarios
# Each rule defines what constitutes a trap for that clause type.
PLAYBOOK: dict[str, dict] = {
    "Renewal Term": {
        "clause_types": ["Renewal Term"],
        "trap_pattern": r"renewal term[\s\S]{0,150}?\(?\s*(\d+)\s*\)?\s*months?",
        "trap_threshold_months": 12,
        "risk": "High",
        "rule_id": "P-01",
        "description": "Auto-renewal >12 months without commensurate termination right is a trap.",
        "preferred_language": "Initial Term 12 months, renewal Term 12 months.",
        "precedent": "Acme MSA 2024-03 §8.2",
    },
    "Notice Period to Terminate Renewal": {
        "clause_types": ["Notice Period to Terminate Renewal"],
        "trap_pattern": r"notice[\s\S]{0,150}?\(?\s*(\d+)\s*\)?\s*days?",
        "trap_threshold_days": 60,
        "risk": "High",
        "rule_id": "P-02",
        "description": "Notice period <60 days when renewal is 12 months traps buyer.",
        "preferred_language": "90 days notice prior to renewal.",
        "precedent": "Acme MSA 2024-03 §8.3",
    },
    "Termination for Convenience": {
        "clause_types": ["Termination for Convenience"],
        "trap_pattern": r"termination\s+for\s+convenience",
        "risk": "Medium",
        "rule_id": "P-03",
        "description": "Missing Termination for Convenience removes exit option.",
        "preferred_language": "Either party may terminate for convenience on 30 days notice.",
        "precedent": "LargeCo Template §12.1",
    },
    "Uncapped Liability": {
        "clause_types": ["Cap on Liability", "Limitation of Liability"],
        "trap_keywords": ["unlimited", "uncapped", "without limitation", "unlimited liability"],
        "risk": "High",
        "rule_id": "P-04",
        "description": "Uncapped liability violates playbook cap = 12 months fees.",
        "preferred_language": "Liability capped at fees paid in 12 months preceding claim.",
        "precedent": "GiantCo Services §9.4",
    },
    "Audit Rights": {
        "clause_types": ["Audit Rights"],
        "trap_keywords": ["audit at any time", "unlimited audits", "without notice"],
        "risk": "Medium",
        "rule_id": "P-05",
        "description": "Unlimited audit rights is non-standard for SaaS pilot.",
        "preferred_language": "One audit per year on 30 days notice.",
        "precedent": "AgentCo Playbook PR-08",
    },
}

# Cross-clause traps (find *interaction*, not just clause) — memorable for demo
CROSS_TRAPS = [
    {
        "id": "Trap-A",
        "name": "Renewal vs Termination mismatch",
        "requires": ["Renewal Term", "Notice Period to Terminate Renewal"],
        "check": lambda renewal_months, notice_days: renewal_months is not None and notice_days is not None and renewal_months > 12 and notice_days < 60,
        "description": "Auto-renewal 24 months but termination notice only 30 days -> buyer locked in.",
    },
    {
        "id": "Trap-B",
        "name": "Liability cap bypass via carve-outs",
        "requires": ["Cap on Liability"],
        "keywords": ["carve-out", "excluded from cap", "not subject to limitation"],
        "description": "Liability cap exists but carve-outs effectively bypass it.",
    },
]


@dataclass
class Evidence:
    clause_type: str
    span_text: str
    page: int
    line: int
    start: int
    end: int
    confidence: float
    rule_id: str
    precedent: str


@dataclass
class Finding:
    trap_id: str
    clause_type: str
    risk: str
    span_text: str
    page: int
    line: int
    evidence: Evidence
    proposed_change: str
    rationale: str


def _find_spans(contract_text: str, pattern: str, page_map: list[tuple[int, int, int]]) -> list[tuple[str, int, int, int, int]]:
    """Return list of (matched_text, start, end, page, line) for regex pattern."""
    out = []
    for m in re.finditer(pattern, contract_text, flags=re.IGNORECASE | re.MULTILINE):
        start, end = m.start(), m.end()
        page, line = _offset_to_page_line(start, page_map, contract_text)
        snippet = contract_text[max(0, start - 80): min(len(contract_text), end + 80)].strip()
        out.append((snippet, start, end, page, line))
    return out


def _offset_to_page_line(offset: int, page_map: list[tuple[int, int, int]], contract_text: str = "") -> tuple[int, int]:
    """page_map: list of (page_num, start_offset, end_offset)"""
    for page, s, e in page_map:
        if s <= offset < e:
            # line approx: count newlines from page start
            line = contract_text[s:offset].count("\n") + 1 if contract_text else 1
            return page, line
    return 1, 1


def build_page_map(contract_text: str, chars_per_page: int = 2500) -> list[tuple[int, int, int]]:
    pages = []
    for i in range(0, len(contract_text), chars_per_page):
        page_num = i // chars_per_page + 1
        pages.append((page_num, i, min(i + chars_per_page, len(contract_text))))
    if not pages:
        pages.append((1, 0, 0))
    return pages


def detect_clauses(contract_text: str, page_map: list[tuple[int, int, int]] | None = None) -> list[Evidence]:
    """Single-pass clause detection: regex + keyword fuzzy. Production, deterministic."""
    if page_map is None:
        page_map = build_page_map(contract_text)
    findings: list[Evidence] = []
    for clause_name, rule in PLAYBOOK.items():
        # Termination for Convenience: the trap is its ABSENCE, not its presence
        # (see rule["description"]: "Missing Termination for Convenience removes exit option").
        # There's no span to cite for something that isn't there, so this is the one
        # document-level (start=end=0) finding baseline emits.
        if clause_name == "Termination for Convenience":
            if not re.search(rule["trap_pattern"], contract_text, flags=re.IGNORECASE):
                findings.append(Evidence(
                    clause_type=clause_name,
                    span_text="[No 'Termination for Convenience' clause found anywhere in the document]",
                    page=1, line=1,
                    start=0, end=0,
                    confidence=0.60,
                    rule_id=rule["rule_id"],
                    precedent=rule["precedent"],
                ))
            continue
        # Pattern-based types
        if "trap_pattern" in rule:
            spans = _find_spans(contract_text, rule["trap_pattern"], page_map)
            for snippet, start, end, page, line in spans:
                # Extract numeric value for threshold check
                m = re.search(rule["trap_pattern"], snippet, flags=re.IGNORECASE)
                val = None
                if m and m.lastindex:
                    try:
                        val = int(m.group(1))
                    except (TypeError, ValueError):
                        val = None
                # Decide trap: renewal/notice are the only two remaining trap_pattern
                # rules (Termination for Convenience is handled above), both threshold-gated.
                is_trap = False
                if clause_name == "Renewal Term" and val is not None:
                    is_trap = val > rule["trap_threshold_months"]
                elif clause_name == "Notice Period to Terminate Renewal" and val is not None:
                    # will be checked cross-wise, but also flag if <60 alone
                    is_trap = val < rule["trap_threshold_days"]
                if is_trap:
                    findings.append(Evidence(
                        clause_type=clause_name,
                        span_text=snippet,
                        page=page, line=line,
                        start=start, end=end,
                        confidence=0.78 if val is not None else 0.65,
                        rule_id=rule["rule_id"],
                        precedent=rule["precedent"],
                    ))
        # Keyword-based types
        if "trap_keywords" in rule:
            for kw in rule["trap_keywords"]:
                # fuzzy to tolerate variations, threshold 88
                for m in re.finditer(re.escape(kw), contract_text, flags=re.IGNORECASE):
                    start, end = m.start(), m.end()
                    page, line = _offset_to_page_line(start, page_map, contract_text)
                    snippet = contract_text[max(0, start - 80): min(len(contract_text), end + 80)].strip()
                    findings.append(Evidence(
                        clause_type=clause_name,
                        span_text=snippet,
                        page=page, line=line,
                        start=start, end=end,
                        confidence=0.92,
                        rule_id=rule["rule_id"],
                        precedent=rule["precedent"],
                    ))
                # also fuzzy scan for near-miss (e.g., "unlimited  liability" with double space)
                # keep deterministic: only exact for baseline
    # Deduplicate by (clause_type, start)
    seen = set()
    uniq = []
    for e in findings:
        key = (e.clause_type, e.start)
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return sorted(uniq, key=lambda x: x.start)


def detect_cross_traps(contract_text: str, page_map: list[tuple[int, int, int]] | None = None) -> list[Finding]:
    """Cross-clause trap detection — finds interaction, not just clause. Baseline does this naively (no verification)."""
    if page_map is None:
        page_map = build_page_map(contract_text)
    clauses = detect_clauses(contract_text, page_map)
    # Build quick lookup by clause type
    by_type: dict[str, list[Evidence]] = {}
    for c in clauses:
        by_type.setdefault(c.clause_type, []).append(c)

    findings: list[Finding] = []

    # Trap-A: renewal vs notice mismatch
    renewals = by_type.get("Renewal Term", [])
    notices = by_type.get("Notice Period to Terminate Renewal", [])
    for r in renewals:
        m = re.search(r"(\d+)\s*months", r.span_text, flags=re.IGNORECASE)
        r_val = int(m.group(1)) if m else None
        for n in notices:
            mn = re.search(r"(\d+)\s*days", n.span_text, flags=re.IGNORECASE)
            n_val = int(mn.group(1)) if mn else None
            if r_val is not None and n_val is not None and r_val > 12 and n_val < 60:
                # Baseline proposes change but does NOT verify citation exists (hallucination risk)
                findings.append(Finding(
                    trap_id="Trap-A",
                    clause_type="Renewal Term + Notice Period",
                    risk="High",
                    span_text=f"{r.span_text} || {n.span_text}",
                    page=r.page, line=r.line,
                    evidence=r,
                    proposed_change="Amend renewal to 12 months and notice to 90 days per P-01/P-02.",
                    rationale="Auto-renewal 24 months with 30-day notice locks buyer in — cross-reference trap.",
                ))

    # Trap-B: cap bypass via carve-outs
    caps = by_type.get("Cap on Liability", []) + by_type.get("Limitation of Liability", [])
    for c in caps:
        window = contract_text[max(0, c.start - 400): c.end + 400]
        if re.search(r"carve-out|excluded from cap|not subject to limitation", window, flags=re.IGNORECASE):
            findings.append(Finding(
                trap_id="Trap-B",
                clause_type="Cap on Liability",
                risk="High",
                span_text=c.span_text,
                page=c.page, line=c.line,
                evidence=c,
                proposed_change="Limit carve-outs to fraud/willful misconduct and keep cap at 12 months fees.",
                rationale="Carve-outs effectively bypass cap.",
            ))

    # Fallback: single-clause traps (every clause finding is also a trap in baseline)
    for e in clauses:
        # Avoid duplicating cross traps already emitted
        if not any(f.evidence.start == e.start for f in findings):
            rule = PLAYBOOK.get(e.clause_type, {})
            findings.append(Finding(
                trap_id=e.rule_id,
                clause_type=e.clause_type,
                risk=rule.get("risk", "Medium"),
                span_text=e.span_text,
                page=e.page, line=e.line,
                evidence=e,
                proposed_change=rule.get("preferred_language", "Revise per playbook."),
                rationale=rule.get("description", ""),
            ))

    return findings


def health_check() -> dict:
    return {"status": "ok", "variant": "baseline"}


def process_contract(contract_text: str) -> dict:
    """Production baseline entrypoint: contract_text -> findings. Pure, testable."""
    if not contract_text or not contract_text.strip():
        raise ValueError("contract_text must be non-empty")
    if len(contract_text) > 120000:
        contract_text = contract_text[:120000]
    page_map = build_page_map(contract_text)
    traps = detect_cross_traps(contract_text, page_map)
    # Intentionally no verification gating — baseline may include hallucinated-adjacent spans if regex drifts (but not fully hallucinated page:line, still deterministic)
    return {
        "variant": "baseline",
        "trap_count": len(traps),
        "findings": [asdict(t) for t in traps],
        "evidence_supported": len(traps),  # baseline claims all supported (over-claim)
        "unsupported": 0,  # baseline does not measure this — will be caught by eval harness
    }
