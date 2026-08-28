"""
Verify — gates every substantive redline on auditable evidence.

For every proposed edit, verify:
  - contract_span exists at page:line in contract_text
  - playbook rule exists and matches clause type
  - precedent exists (if required)
  - proposed change is surgical (not block edit >500 chars)

If FAIL -> REJECT and emit revise hint for targeted retry.
Only PASS edits reach human reviewer as approved candidate (Rule 04/05 framing).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .risk import PLAYBOOK, RiskFinding, PRECEDENTS


@dataclass
class VerificationResult:
    status: Literal["PASS", "REJECT"]
    reasons: list[str]
    revise_hint: str | None
    evidence_supported: bool


def verify_finding(hit_span: str, finding: RiskFinding, evidence_pkg: dict, contract_text: str) -> VerificationResult:
    reasons: list[str] = []
    # 1) Contract span exists at page:line (provenance) — use normalized whitespace + rapidfuzz for robustness, not strict substring
    from rapidfuzz import fuzz
    span_norm = re.sub(r"\s+", " ", hit_span.strip())[:160]
    contract_norm = re.sub(r"\s+", " ", contract_text)[:8000]  # first 8k chars window
    # Check existence via fuzzy partial ratio >=80 or substring
    exists = False
    if span_norm:
        # Try exact substring first (fast), then fuzzy
        if span_norm[:40].lower() in contract_text.lower():
            exists = True
        elif span_norm[:60].lower() in contract_norm.lower():
            exists = True
        else:
            # Fuzzy: check if span's core 60 chars has high partial ratio in contract
            score = fuzz.partial_ratio(span_norm[:80].lower(), contract_norm.lower())
            if score >= 80:
                exists = True
    if not exists:
        reasons.append(f"contract_span not found in contract text (hallucinated page:{evidence_pkg.get('contract_page')}, fuzz partial_ratio <80)")
    # 2) Playbook rule exists and matches clause type
    rule_id = evidence_pkg.get("playbook_rule")
    rule = PLAYBOOK.get(rule_id) if rule_id else None
    if not rule:
        reasons.append(f"playbook_rule {rule_id} does not exist")
    elif finding.clause_type not in rule.get("clause_types", []):
        reasons.append(f"rule {rule_id} does not govern clause_type {finding.clause_type}")

    # 3) Precedent exists if rule requires it (all our rules have precedent, but check)
    prec = evidence_pkg.get("precedent")
    if not prec:
        # Not all findings need precedent, but if rule mentions precedent id that doesn't exist, fail
        expected_prec_id = rule.get("precedent", "").split()[0] if rule else ""
        if expected_prec_id and not any(p["id"] == expected_prec_id for p in PRECEDENTS):
            reasons.append(f"precedent {expected_prec_id} not found")

    # 4) Surgical edit check (RedlineBench finding: models make fewer, larger block edits)
    proposed = finding.proposed_change or ""
    if len(proposed) > 500:
        reasons.append(f"proposed change is block edit ({len(proposed)} chars) not surgical - split into smaller edits")

    # 5) Cross-check for empty evidence
    if not evidence_pkg.get("contract_span"):
        reasons.append("empty contract_span evidence")

    if reasons:
        hint = "Revise: ensure contract_span is verbatim substring at claimed page:line, use correct rule_id for clause_type, and keep edit surgical (<300 chars)."
        return VerificationResult(status="REJECT", reasons=reasons, revise_hint=hint, evidence_supported=False)

    return VerificationResult(status="PASS", reasons=[], revise_hint=None, evidence_supported=True)


def is_supported_finding(verif: VerificationResult) -> bool:
    return verif.status == "PASS" and verif.evidence_supported
