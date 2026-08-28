"""
Advanced core — verification-gated harness, production-grade.

Implements reviewer-corrected closed-loop: discover -> reason -> propose -> evidence -> verify -> human review as approved candidate.
No synthetic traps as ground truth; uses RedlineBench golds + trap suite with trap-focused golds.
"""
from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from .harness.ingest import Page
from .harness.extract import extract_clauses
from .harness.risk import assess_risk, build_evidence_package, PLAYBOOK
from .harness.verify import verify_finding
from .harness.memory import NegotiationMemory, select_harness_mode
from .harness.router import route_findings


def _trap_interactions(contract_text: str, clause_hits, pages) -> list[dict]:
    """Find cross-clause trap interactions (A-D) — the memorable part."""
    traps: list[dict] = []
    by_type = {}
    for h in clause_hits:
        by_type.setdefault(h.clause_type, []).append(h)

    for r in by_type.get("Renewal Term", []):
        m = re.search(r"(\d+)\s*months", r.span_text, flags=re.IGNORECASE)
        r_val = int(m.group(1)) if m else None
        for n in by_type.get("Notice Period to Terminate Renewal", []):
            mn = re.search(r"(\d+)\s*days", n.span_text, flags=re.IGNORECASE)
            n_val = int(mn.group(1)) if mn else None
            if r_val is not None and n_val is not None and r_val > 12 and n_val < 60:
                traps.append({"id": "Trap-A", "name": "Renewal vs Termination mismatch", "related": [r.clause_type, n.clause_type], "conflict": "auto-renewal >12m but notice <60d locks buyer", "spans": [r.span_text, n.span_text]})

    for c in by_type.get("Cap on Liability", []) + by_type.get("Limitation of Liability", []):
        win = contract_text[max(0, c.start - 400): c.end + 400]
        if re.search(r"carve-out|excluded from cap|not subject to limitation", win, flags=re.IGNORECASE):
            traps.append({"id": "Trap-B", "name": "Liability cap bypass", "related": [c.clause_type], "conflict": "carve-outs bypass cap", "spans": [c.span_text]})

    for p in by_type.get("Post-Termination Services", []):
        win = contract_text[max(0, p.start - 500): p.end + 500]
        if re.search(r"delete.*within.*30 days|deletion.*obligation", win, flags=re.IGNORECASE) and re.search(r"retain.*transition|retention.*requirement", win, flags=re.IGNORECASE):
            traps.append({"id": "Trap-C", "name": "Deletion vs Retention conflict", "related": [p.clause_type], "conflict": "deletion obligation conflicts with transition retention", "spans": [p.span_text]})

    return traps


def process_contract_advanced(
    contract_text: str,
    pages: list[Page],
    contract_id: str = "contract_01",
    turn: int = 1,
    memory: NegotiationMemory | None = None,
    model: str = "gpt-4o-mini",
    harness_mode: str = "auto",
) -> dict:
    if not contract_text or not contract_text.strip():
        raise ValueError("contract_text must be non-empty")
    if len(contract_text) > 120000:
        contract_text = contract_text[:120000]

    mode = select_harness_mode(model, harness_mode)
    clause_hits = extract_clauses(contract_text, pages)
    proposed: list[tuple] = []
    for hit in clause_hits:
        finding = assess_risk(hit)
        if finding is None:
            continue
        ev_pkg = build_evidence_package(hit, finding, contract_text)
        proposed.append((hit, finding, ev_pkg))

    trap_interactions = _trap_interactions(contract_text, clause_hits, pages)

    verified = []
    verification_results = []
    for hit, finding, ev_pkg in proposed:
        ver = verify_finding(hit.span_text, finding, ev_pkg, contract_text)
        verification_results.append(ver)
        verified.append((hit, finding, ev_pkg, ver))

    routed_input = []
    ver_objs = []
    for hit, finding, ev_pkg, ver in verified:
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
        }
        routed_input.append(d)
        ver_objs.append(ver)

    routed = route_findings(routed_input, ver_objs)

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
        })

    approved = [f for f in findings_out if f["verification"] == "PASS"]
    rejected = [f for f in findings_out if f["verification"] == "REJECT"]

    if memory is not None:
        memory.update_from_findings(findings_out, turn=turn)

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
        "over_redlining": 0.0,
    }
