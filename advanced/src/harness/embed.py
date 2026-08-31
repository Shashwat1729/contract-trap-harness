"""
Real semantic embedding client -- hosted Gemini embedding model via litellm.

Why this exists: extract.py's CLAUSE_PATTERNS is regex-only, and real legal drafting
uses more phrasings than any hand-written pattern set can enumerate (this is the
documented recall ceiling in README.md's "Main failure mode"). This module adds a
genuine semantic layer: real embeddings from a hosted model (gemini-embedding-001,
3072-dim), not a hand-rolled similarity heuristic, so extraction can catch a clause
whose wording nobody anticipated but whose *meaning* matches a known clause type.

Mirrors llm.py's contract exactly: mock-gracefully if EVAL_MOCK=1 or no key is
present (embed_available() mirrors llm_available()), retried with backoff, never
raises to the caller. A hosted API was chosen over a local sentence-transformers
model because the local model's dependency chain (torch->scipy->scikit-learn)
requires numpy>=2 while this machine's shared global Python environment already
has numpy pinned to <2 for an unrelated package (streamlit) -- installing it would
have meant editing a shared interpreter used by other, unrelated projects on this
machine, which is exactly the kind of hard-to-reverse, blast-radius-beyond-this-repo
change to avoid. The hosted call reuses infrastructure (litellm, GEMINI key) already
in this codebase and needs no new local dependency at all.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from . import keys as _keys

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

logger = logging.getLogger("advanced.harness.embed")

EMBED_MODEL: str = os.getenv("EMBED_MODEL", "gemini/gemini-embedding-001")
_EVAL_MOCK: bool = os.getenv("EVAL_MOCK", "0") == "1"
_KEY_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY", "OPENAI_API_KEY")


def embed_available() -> bool:
    if _EVAL_MOCK:
        return False
    if _keys.has_any_key():
        return True
    return any(os.getenv(k) for k in _KEY_ENV_VARS)


class EmbedCallError(Exception):
    """Raised internally when the network call fails after retries."""


# Free-tier embedContent quota is observed as PerProject, not PerKey (see the
# QuotaFailure detail's quotaId: "EmbedContentRequestsPerDayPerUserPerProjectPerModel
# -FreeTier" / generation's analogous "...PerProject..." -- confirmed empirically: all
# 5 configured keys failed generate_content identically once the pool was exhausted).
# Multiple keys therefore do NOT multiply the effective per-minute rate -- pacing stays
# fixed regardless of key count; rotation only helps if one specific key is individually
# revoked/invalid, not for spreading load across a shared project quota.
_MIN_INTERVAL_S = 1.5  # ~40 req/min, well under the 100/min free-tier cap
_last_call_ts = 0.0


def _pace() -> None:
    global _last_call_ts
    elapsed = time.monotonic() - _last_call_ts
    if elapsed < _MIN_INTERVAL_S:
        time.sleep(_MIN_INTERVAL_S - elapsed)
    _last_call_ts = time.monotonic()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
def _embed_one(texts: list[str], api_key: str | None) -> list[list[float]]:
    import litellm  # imported lazily, mirrors llm.py

    litellm.suppress_debug_info = True
    _pace()
    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["api_key"] = api_key
    resp = litellm.embedding(model=EMBED_MODEL, input=texts, timeout=30, **kwargs)
    return [d["embedding"] for d in resp.data]


def _embed_raw(texts: list[str]) -> list[list[float]]:
    """Rotates across the same key pool as llm.py (see keys.py) on RateLimitError."""
    import litellm

    if not _keys.has_any_key():
        return _embed_one(texts, api_key=None)

    last_err: Exception | None = None
    attempts = 0
    max_attempts = max(len(_keys.all_keys()) * 2, 1)
    while attempts < max_attempts:
        key = _keys.next_key()
        if key is None:
            break
        attempts += 1
        try:
            return _embed_one(texts, api_key=key)
        except litellm.RateLimitError as e:  # type: ignore[attr-defined]
            last_err = e
            _keys.mark_exhausted(key, str(e))
            continue
    raise last_err or EmbedCallError("no Gemini API keys available (all exhausted or none configured)")


def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]] | None:
    """
    Embed a list of texts, batched. Returns None (never raises) if unavailable
    (EVAL_MOCK / no key) or the call fails after retries across the whole key pool --
    callers must treat None as "semantic layer skipped, regex-only result stands,"
    never as an error.
    """
    if not texts:
        return []
    if not embed_available():
        logger.info("embed unavailable (EVAL_MOCK or no key) -- skipping semantic layer, model=%s", EMBED_MODEL)
        return None
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            out.extend(_embed_raw(chunk))
        return out
    except Exception as e:  # noqa - any failure degrades to "no semantic layer," never crashes the caller
        logger.warning("embed_texts failed for model=%s: %s -- semantic layer skipped", EMBED_MODEL, e)
        return None
