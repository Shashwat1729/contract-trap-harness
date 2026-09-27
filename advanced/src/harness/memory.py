"""
Memory -- structured negotiation memory for turns 2-4.

Holds: accepted positions, rejected positions, open issues, concessions, counterparty asks, deal-breakers, unresolved threads.
Testable: stateless vs memory on later turns.

Upgraded: thinking logs, production-grade type hints / logging.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("advanced.harness.memory")

THINKING_LOG: list[dict[str, Any]] = []
_THINKING_MAX = 200


def _log_thinking(stage: str, input_data: Any, output_data: Any, reasoning: str) -> None:
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "input": str(input_data)[:1200] if input_data is not None else None,
            "output": str(output_data)[:1200] if output_data is not None else None,
            "reasoning": reasoning,
            "mono_ms": int(time.perf_counter() * 1000),
        }
        THINKING_LOG.append(entry)
        if len(THINKING_LOG) > _THINKING_MAX:
            del THINKING_LOG[0 : len(THINKING_LOG) - _THINKING_MAX]
    except Exception as e:
        logger.warning("memory thinking log failed: %s", e)


def get_thinking_log(limit: int = 50) -> list[dict[str, Any]]:
    try:
        return THINKING_LOG[-limit:]
    except Exception:
        return []


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
    prior_findings: list[dict[str, Any]] = field(default_factory=list)

    def to_context(self) -> str:
        try:
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
            ctx = "\n".join(parts) if len(parts) > 1 else "No prior negotiation memory."
            _log_thinking("memory/to_context", self.contract_id, ctx[:500], f"Memory context for {self.contract_id} turn {self.turn}: {len(parts)-1} sections")
            return ctx
        except Exception as e:
            logger.exception("to_context failed for %s: %s", self.contract_id, e)
            return f"Memory error for {self.contract_id}: {e}"

    def update_from_findings(self, findings: list[dict[str, Any]], turn: int) -> None:
        try:
            self.turn = turn
            prev_open = len(self.open_issues)
            for f in findings:
                key = f.get("rule_id") or f.get("clause_type", "")
                if f.get("risk") == "High":
                    if key not in self.open_issues and key not in self.accepted_positions:
                        self.open_issues.append(key)
                self.prior_findings.append(f)
            _log_thinking("memory/update", f"{len(findings)} findings turn={turn}", f"open_issues {prev_open}->{len(self.open_issues)} total {len(self.prior_findings)}", f"Updated memory {self.contract_id} turn {turn}: +{len(findings)} findings, open {prev_open}->{len(self.open_issues)}")
            logger.info("memory %s turn %d updated %d findings open=%d total=%d", self.contract_id, turn, len(findings), len(self.open_issues), len(self.prior_findings))
        except Exception as e:
            logger.exception("update_from_findings failed for %s: %s", self.contract_id, e)
            _log_thinking("memory/update_error", str(findings)[:500], str(e), f"update failed: {e}")


# Tier-aware harness selector (supporting experiment, not main thesis)
def select_harness_mode(model: str, requested: str = "auto") -> str:
    """Light for frontier chat (Gemini Flash-like), balanced for others. Per HEAT-24 paradox."""
    try:
        if requested in ("light", "balanced", "strict"):
            _log_thinking("memory/select_mode", f"model={model} requested={requested}", requested, f"Explicit harness_mode {requested} requested")
            return requested
        m = model.lower()
        if any(x in m for x in ["gemini", "flash", "gpt-5", "gpt-4o"]):
            _log_thinking("memory/select_mode", model, "light", f"Frontier chat {model} -> light (verbose hurts -29-38 pts)")
            return "light"  # frontier chat -> verbose hurts -29-38 pts
        if any(x in m for x in ["haiku", "sonnet", "mini", "3.5"]):
            _log_thinking("memory/select_mode", model, "balanced", f"Efficient model {model} -> balanced")
            return "balanced"
        _log_thinking("memory/select_mode", model, "balanced", f"Default balanced for {model}")
        return "balanced"
    except Exception as e:
        logger.warning("select_harness_mode fallback: %s", e)
        _log_thinking("memory/select_mode_error", str(model)[:100], "balanced", f"select_mode exception {e} -> balanced")
        return "balanced"

