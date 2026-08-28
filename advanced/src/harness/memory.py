"""
Memory — structured negotiation memory for turns 2-4.

Holds: accepted positions, rejected positions, open issues, concessions, counterparty asks, deal-breakers, unresolved threads.
Testable: stateless vs memory on later turns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class NegotiationMemory:
    contract_id: str
    turn: int
    accepted_positions: list[str] = field(default_factory=list)
    rejected_positions: list[str] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    concessions: list[str] = field(default_factory=list)
    counterparty_asks: list[str] = field(default_factory=list)
    deal_breakers: list[str] = field(default_factory=list)
    unresolved_threads: list[str] = field(default_factory=list)
    prior_findings: list[dict] = field(default_factory=list)

    def to_context(self) -> str:
        parts = [f"Negotiation memory for {self.contract_id} turn {self.turn}:"]
        if self.accepted_positions:
            parts.append("Accepted: " + "; ".join(self.accepted_positions))
        if self.rejected_positions:
            parts.append("Rejected: " + "; ".join(self.rejected_positions))
        if self.open_issues:
            parts.append("Open issues: " + "; ".join(self.open_issues))
        if self.concessions:
            parts.append("Concessions: " + "; ".join(self.concessions))
        if self.counterparty_asks:
            parts.append("Counterparty asks: " + "; ".join(self.counterparty_asks))
        if self.deal_breakers:
            parts.append("Deal-breakers: " + "; ".join(self.deal_breakers))
        if self.unresolved_threads:
            parts.append("Unresolved threads: " + "; ".join(self.unresolved_threads))
        return "\n".join(parts) if len(parts) > 1 else "No prior negotiation memory."

    def update_from_findings(self, findings: list[dict], turn: int):
        self.turn = turn
        for f in findings:
            key = f.get("rule_id") or f.get("clause_type", "")
            if f.get("risk") == "High":
                if key not in self.open_issues and key not in self.accepted_positions:
                    self.open_issues.append(key)
            self.prior_findings.append(f)


# Tier-aware harness selector (supporting experiment, not main thesis)
def select_harness_mode(model: str, requested: str = "auto") -> str:
    """Light for frontier chat (Gemini Flash-like), balanced for others. Per HEAT-24 paradox."""
    if requested in ("light", "balanced", "strict"):
        return requested
    # auto: heuristic
    m = model.lower()
    if any(x in m for x in ["gemini", "flash", "gpt-5", "gpt-4o"]):
        return "light"  # frontier chat -> verbose hurts -29-38 pts
    if any(x in m for x in ["haiku", "sonnet", "mini", "3.5"]):
        return "balanced"
    return "balanced"
