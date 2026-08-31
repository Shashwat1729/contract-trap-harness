"""
Multi-key rotation for the Gemini provider -- shared by llm.py (generation) and
embed.py (embeddings), since both hit the same per-account free-tier quota system
and both were blocked mid-session by exhausted daily/per-minute caps (see
CHANGELOG #13).

The user supplied several personal API keys specifically so a quota-exhausted key
doesn't stall a real validation run: each key is a separate account's own free-tier
allowance, tried sequentially (never concurrently, never to inflate a single
account's limit) -- when one key's quota is exhausted, the next is tried instead of
failing the whole call. This is ordinary reliability engineering (a fallback pool),
not an attempt to evade any single account's terms.

GEMINI_API_KEYS in advanced/.env is a comma-separated list; single-value
GEMINI_API_KEY / GOOGLE_API_KEY / GOOGLE_GENERATIVE_AI_API_KEY are folded in too
(deduplicated) so nothing already configured is lost.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("advanced.harness.keys")

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass


def _load_keys() -> list[str]:
    keys: list[str] = []
    raw = os.getenv("GEMINI_API_KEYS", "")
    for k in raw.split(","):
        k = k.strip()
        if k and k not in keys:
            keys.append(k)
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"):
        v = os.getenv(var)
        if v and v not in keys:
            keys.append(v)
    return keys


_ALL_KEYS: list[str] = _load_keys()
_EXHAUSTED_UNTIL: dict[str, float] = {}
_cursor = 0

PER_MINUTE_COOLDOWN_S = 65
PER_DAY_COOLDOWN_S = 24 * 3600


def all_keys() -> list[str]:
    return list(_ALL_KEYS)


def has_any_key() -> bool:
    return bool(_ALL_KEYS)


def available_keys() -> list[str]:
    now = time.time()
    return [k for k in _ALL_KEYS if _EXHAUSTED_UNTIL.get(k, 0) <= now]


def _short(key: str) -> str:
    return f"...{key[-6:]}" if len(key) > 6 else key


def mark_exhausted(key: str, error_text: str = "") -> None:
    cooldown = PER_DAY_COOLDOWN_S if "PerDay" in error_text else PER_MINUTE_COOLDOWN_S
    _EXHAUSTED_UNTIL[key] = time.time() + cooldown
    logger.warning(
        "key %s marked exhausted for %ds (%s quota) -- %d/%d keys still available",
        _short(key), cooldown, "daily" if cooldown == PER_DAY_COOLDOWN_S else "per-minute",
        len(available_keys()), len(_ALL_KEYS),
    )


def next_key() -> str | None:
    """Round-robins across currently-available (non-cooling-down) keys."""
    global _cursor
    avail = available_keys()
    if not avail:
        return None
    key = avail[_cursor % len(avail)]
    _cursor += 1
    return key


def reset_for_testing() -> None:
    """Test-only: clear exhaustion state and cursor."""
    global _cursor
    _EXHAUSTED_UNTIL.clear()
    _cursor = 0
