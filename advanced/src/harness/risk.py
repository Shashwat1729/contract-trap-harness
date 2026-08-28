"""
Risk — playbook + precedent retrieval with evidence package.

Playbook is 12 SaaS rules (P-01..P-12) grounded in CUAD handbook + RedlineBench commerce context.
Precedent store is tiny in fixtures (Acme, LargeCo, GiantCo) — production BM25-style via rapidfuzz, no heavy index needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re

from rapidfuzz import fuzz

from .extract import ClauseHit

# Production playbook — each rule defines what constitutes a trap and preferred language
PLAYBOOK: dict[str, dict] = {
    "P-01": {"clause_types": ["Renewal Term"], "trap": "renewal >12 months", "preferred": "Initial Term 12 months, renewal Term 12 months.", "commercial": "Pilot must not lock in; 12m is market.", "precedent": "Acme MSA 2024-03 §8.2"},
    "P-02": {"clause_types": ["Notice Period to Terminate Renewal"], "trap": "notice <60 days with 12m renewal", "preferred": "90 days notice prior to renewal.", "commercial": "Ops needs 90 days to evaluate alternatives.", "precedent": "Acme MSA 2024-03 §8.3"},
    "P-03": {"clause_types": ["Termination for Convenience"], "trap": "missing TFC", "preferred": "Either party may terminate for convenience on 30 days notice.", "commercial": "TalentFlow is pilot, needs exit.", "precedent": "LargeCo Template §12.1"},
    "P-04": {"clause_types": ["Cap on Liability", "Limitation of Liability"], "trap": "uncapped / unlimited", "preferred": "Liability capped at fees paid in 12 months preceding claim.", "commercial": "Series A cannot bear uncapped.", "precedent": "GiantCo Services §9.4"},
    "P-05": {"clause_types": ["Audit Rights"], "trap": "unlimited audits / any time without notice", "preferred": "One audit per year on 30 days notice.", "commercial": "Ops burden for pilot.", "precedent": "AgentCo Playbook PR-08"},
    "P-06": {"clause_types": ["Governing Law"], "trap": "vendor-favorable jurisdiction without mutuality", "preferred": "Delaware, mutual.", "commercial": "AgentCo is Delaware C-Corp.", "precedent": "LargeCo MSA §14.1"},
    "P-07": {"clause_types": ["License Grant"], "trap": "irrevocable/perpetual without termination linkage", "preferred": "License terminates on termination.", "commercial": "No perpetual after exit.", "precedent": "AgentCo MSA §3.1"},
    "P-08": {"clause_types": ["Non-Compete"], "trap": "broad non-compete >12 months / non-market", "preferred": "Narrow to direct competitors, 6 months.", "commercial": "TalentFlow is HR tech, broad non-compete blocks GTM.", "precedent": "AgentCo Playbook PR-11"},
    "P-09": {"clause_types": ["Non-Disparagement"], "trap": "one-way disparagement only", "preferred": "Mutual non-disparagement.", "commercial": "Mutuality for enterprise deal.", "precedent": "LargeCo §11.4"},
    "P-10": {"clause_types": ["IP Ownership Assignment"], "trap": "vendor owns customer data/IP", "preferred": "Customer retains IP, vendor retains platform IP.", "commercial": "TalentFlow is core HR data.", "precedent": "AgentCo Playbook PR-02"},
    "P-11": {"clause_types": ["Post-Termination Services"], "trap": "no transition assistance / conflicting retention", "preferred": "30 days transition at prior rates.", "commercial": "Need offboarding window.", "precedent": "GiantCo §7.3"},
    "P-12": {"clause_types": ["Limitation of Liability"], "trap": "carve-outs bypass cap (e.g., excluded from cap)", "preferred": "Carve-outs limited to fraud/willful misconduct.", "commercial": "Carve-outs that bypass cap defeat purpose.", "precedent": "Acme §9.5"},
}

# In-memory precedent corpus (tiny, production would be vector DB; this is deterministic + reproducible + no heavy dep)
PRECEDENTS = [
    {"id": "PR-01", "title": "Acme MSA 2024-03 §8.2 Renewal", "text": "Renewal Term 12 months, 90 days notice. Liability capped at 12 months fees."},
    {"id": "PR-02", "title": "LargeCo Template §12.1 TFC", "text": "Either party may terminate for convenience on 30 days written notice."},
    {"id": "PR-03", "title": "GiantCo Services §9.4 Liability", "text": "Liability cap = fees paid in 12 months preceding claim, carve-outs limited to fraud."},
    {"id": "PR-04", "title": "AgentCo Playbook PR-08 Audit", "text": "One audit per year on 30 days notice, during business hours."},
    {"id": "PR-08", "title": "AgentCo Playbook PR-11 Non-Compete", "text": "Non-compete limited to direct competitors, 6 months, geography US."},
]


@dataclass
class RiskFinding:
    clause_type: str
    risk: str
    rule_id: str
    precedent_id: str
    proposed_change: str
    rationale: str
    confidence: float
    # Evidence package fields for verifier
    evidence_contract_span: str
    evidence_page: int
    evidence_line: int


def assess_risk(hit: ClauseHit) -> RiskFinding | None:
    """Map clause hit -> risk finding via playbook. Returns None if not risky."""
    # Direct rule match
    for rid, rule in PLAYBOOK.items():
        if hit.clause_type in rule["clause_types"]:
            # For value-trap types, check threshold
            if hit.clause_type == "Renewal Term":
                m = re.search(r"(\d+)\s*months", hit.span_text, flags=re.IGNORECASE)
                if m and int(m.group(1)) > 12:
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.88, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
                # else not a trap -> no finding (surgical: leave alone)
                return None
            if hit.clause_type == "Notice Period to Terminate Renewal":
                # Trap is <60 days, but need cross-check with renewal; emit finding for verifier to cross-check
                m = re.search(r"(\d+)\s*days", hit.span_text, flags=re.IGNORECASE)
                if m and int(m.group(1)) < 60:
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.84, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
                return None
            # Cap trap via carve-out/bypass (even when matched as pattern, not just trap_value)
            if hit.clause_type in ("Cap on Liability", "Limitation of Liability"):
                if re.search(r"carve-out|excluded from cap|not subject to limitation|bypass.*cap", hit.span_text, flags=re.IGNORECASE):
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.91, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
                # Also check surrounding contract for carve-out near cap (if span is small, check contract window)
                # But for now, also handle uncapped keyword even as pattern
                if re.search(r"uncapped|unlimited", hit.span_text, flags=re.IGNORECASE):
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.91, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
            if hit.match_kind == "trap_value":
                # Keyword trap always risky
                return RiskFinding(
                    clause_type=hit.clause_type, risk="High", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                    proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                    confidence=0.91, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                )
            # Generic clause hit with medium risk (e.g., License Grant irrevocable)
            if hit.clause_type in ("License Grant", "Non-Compete", "IP Ownership Assignment", "Post-Termination Services"):
                # Only flag if span contains trap keywords
                trap_kws = ["irrevocable", "perpetual", "unlimited", "without limitation", "non-compete", "owns.*customer data"]
                if any(re.search(kw, hit.span_text, flags=re.IGNORECASE) for kw in trap_kws):
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.76, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
                return None
            # For Governing Law etc., only flag if vendor-favorable
            if hit.clause_type == "Governing Law" and re.search(r"California|New York", hit.span_text, flags=re.IGNORECASE):
                # simplified: if not Delaware, suggest
                if "Delaware" not in hit.span_text:
                    return RiskFinding(
                        clause_type=hit.clause_type, risk="Medium", rule_id=rid, precedent_id=rule["precedent"].split()[0],
                        proposed_change=rule["preferred"], rationale=rule["commercial"] + " " + rule["trap"],
                        confidence=0.72, evidence_contract_span=hit.span_text, evidence_page=hit.page, evidence_line=hit.line,
                    )
                return None
    return None


def retrieve_precedent(query_text: str, top_k: int = 1) -> list[dict]:
    """BM25-like via rapidfuzz token_set_ratio, deterministic, no heavy index."""
    scored = []
    for p in PRECEDENTS:
        score = fuzz.token_set_ratio(query_text, p["text"])
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:top_k] if s > 45]


def build_evidence_package(hit: ClauseHit, finding: RiskFinding, contract_text: str) -> dict:
    """Evidence package that verifier will gate on."""
    precedent = retrieve_precedent(finding.proposed_change)
    return {
        "contract_span": finding.evidence_contract_span,
        "contract_page": finding.evidence_page,
        "contract_line": finding.evidence_line,
        "contract_exists": finding.evidence_contract_span.strip()[:80] in contract_text if finding.evidence_contract_span else False,
        "playbook_rule": finding.rule_id,
        "playbook_text": PLAYBOOK[finding.rule_id]["trap"] + " -> " + PLAYBOOK[finding.rule_id]["preferred"],
        "commercial_instruction": PLAYBOOK[finding.rule_id]["commercial"],
        "precedent": precedent[0] if precedent else None,
        "confidence": finding.confidence,
    }
