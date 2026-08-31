"""
Fallback / sandbox handler — production, Rule 04.

All consequential redlines are sandboxed; fallback never auto-applies.
Returns a safe, auditable payload for human review.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("advanced.fallback")


def fallback_response(contract_id: str, reason: str) -> dict[str, Any]:
    log.warning("fallback for %s reason=%s", contract_id, reason)
    return {
        "variant": "advanced",
        "contract_id": contract_id,
        "status": "fallback",
        "reason": reason,
        "fallback": True,
        "verified": False,
        "next_step": "Route to human reviewer with original contract and error context. No redline applied.",
        "sandbox": True,
    }
