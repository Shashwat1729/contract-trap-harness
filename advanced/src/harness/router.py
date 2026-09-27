"""
Router -- field-level routing, human checkpoint for consequential actions (Rule 04/05).

Upgraded: thinking logs per RiskWise Developer View.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("advanced.harness.router")

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
        logger.debug("router thinking [%s] %s", stage, reasoning[:100])
        try:
            evidence_dir = Path(__file__).parents[2] / "evidence" / "reviews"
            alt_dir = Path(__file__).parents[1].parent / "evidence" / "reviews"
            for d in (evidence_dir, alt_dir):
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    fp = d / "thinking_router.json"
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(THINKING_LOG[-50:], f, indent=2, ensure_ascii=False)
                    break
                except Exception:
                    continue
        except Exception:
            pass
    except Exception as e:
        logger.warning("router thinking log failed: %s", e)


def get_thinking_log(limit: int = 50) -> list[dict[str, Any]]:
    try:
        return THINKING_LOG[-limit:]
    except Exception:
        return []


@dataclass
class RoutedFinding:
    finding: dict[str, Any]
    route: Literal["human_review"]
    verification: str  # PASS / REJECT
    reasons: list[str]


def route_findings(verified_findings: list[dict[str, Any]], verification_results: list[Any]) -> list[RoutedFinding]:
    """
    Route every finding to human_review -- deliberate, permanent, not a stub for a
    future auto-route path. Rule 04/05 requires a human checkpoint before any
    consequential redline is applied, regardless of verification confidence, so there
    is no PASS/dual_mode combination this function auto-approves. The route field
    exists (rather than being dropped) so downstream consumers (report.py, the
    dashboard) have one stable field name if a second route is ever deliberately
    added -- not because one is currently planned.

    Thinking log captures routing decision per finding.
    """
    t0 = time.perf_counter()
    out: list[RoutedFinding] = []
    try:
        _log_thinking("router/start", f"{len(verified_findings)} findings, {len(verification_results)} verifs", "routing to human_review per Rule 04/05", f"Router start: {len(verified_findings)} findings, all route to human_review")
        for f, v in zip(verified_findings, verification_results):
            try:
                status = v.status if hasattr(v, "status") else v.get("status", "REJECT")
                reasons = v.reasons if hasattr(v, "reasons") else v.get("reasons", [])
                dual_mode = getattr(v, "dual_mode", None) or (v.get("dual_mode") if isinstance(v, dict) else None)
                route: Literal["human_review"] = "human_review"
                out.append(RoutedFinding(finding=f, route=route, verification=status, reasons=reasons))
                _log_thinking("router/single", f"{f.get('clause_type')} ver={status} dual={dual_mode}", f"route={route}", f"Routed {f.get('clause_type')} ver={status} dual={dual_mode} -> {route} reasons={reasons[:1]}")
            except Exception as e:
                logger.warning("route_findings inner failed: %s", e)
                _log_thinking("router/inner_error", str(f)[:300], str(e), f"Inner route failed: {e}")
                continue
        _log_thinking("router/done", f"{len(verified_findings)} in", f"{len(out)} routed in {(time.perf_counter()-t0)*1000:.1f}ms", f"Router done: {len(out)} findings routed to human_review in {(time.perf_counter()-t0)*1000:.1f}ms")
        logger.info("route_findings %d -> %d human_review in %.1fms", len(verified_findings), len(out), (time.perf_counter()-t0)*1000)
    except Exception as e:
        logger.exception("route_findings failed: %s", e)
        _log_thinking("router/error", f"{len(verified_findings)} findings", str(e), f"Router exception {e}, fallback to human_review for all")
        # Graceful fallback: return human_review for all
        for f in verified_findings:
            try:
                out.append(RoutedFinding(finding=f, route="human_review", verification="REJECT", reasons=[f"router fallback: {e}"]))
            except Exception:
                continue
    return out

