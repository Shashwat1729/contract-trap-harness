"""
Router — field-level routing, human checkpoint for consequential actions (Rule 04/05).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class RoutedFinding:
    finding: dict
    route: Literal["auto", "human_review"]
    verification: str  # PASS / REJECT
    reasons: list[str]


def route_findings(verified_findings: list[dict], verification_results: list) -> list[RoutedFinding]:
    out: list[RoutedFinding] = []
    for f, v in zip(verified_findings, verification_results):
        status = v.status if hasattr(v, "status") else v.get("status", "REJECT")
        if status == "PASS":
            # High risk always goes to human as approved candidate (not auto-applied)
            route: Literal["auto", "human_review"] = "human_review"
        else:
            route = "human_review"  # rejected still shown to human with reasons why rejected
        out.append(RoutedFinding(finding=f, route=route, verification=status, reasons=v.reasons if hasattr(v, "reasons") else v.get("reasons", [])))
    return out
