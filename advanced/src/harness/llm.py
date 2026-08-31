"""
LLM client -- provider-agnostic via litellm, single call site for the whole harness.

Swapping providers is a one-line env change (LLM_MODEL), not a code change:
    LLM_MODEL=gemini/gemini-2.5-flash   (default)
    LLM_MODEL=gpt-4o-mini
    LLM_MODEL=claude-haiku-4-5-20251001
litellm reads the matching *_API_KEY env var itself (GEMINI_API_KEY, OPENAI_API_KEY,
ANTHROPIC_API_KEY, ...).

Real network calls are gated: if EVAL_MOCK=1 or no provider key is present, every
call here returns the caller-supplied mock_response instead of hitting the network.
This keeps `make reproduce` / EVAL_MOCK=1 fully offline and $0 for judges without
API keys, while a key holder gets genuine LLM calls with no code change.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from . import keys as _keys

try:  # self-contained: load advanced/.env even if this module is imported before src.config
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

logger = logging.getLogger("advanced.harness.llm")

LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
_EVAL_MOCK: bool = os.getenv("EVAL_MOCK", "0") == "1"
_KEY_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
_IS_GEMINI = LLM_MODEL.startswith("gemini/")


def llm_available() -> bool:
    """True only if a provider key is present AND EVAL_MOCK is not forcing offline mode."""
    if _EVAL_MOCK:
        return False
    if _IS_GEMINI and _keys.has_any_key():
        return True
    return any(os.getenv(k) for k in _KEY_ENV_VARS)


class LLMCallError(Exception):
    """Raised internally when the network call fails after retries; always caught by call_llm_json."""


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def _call_one(messages: list[dict[str, str]], max_tokens: int, temperature: float, api_key: str | None) -> str:
    import litellm  # imported lazily -- keeps import cost out of modules that never call an LLM

    litellm.suppress_debug_info = True
    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["api_key"] = api_key
    resp = litellm.completion(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=int(__import__("os").getenv("LLM_TIMEOUT", "25")),
        **kwargs,
    )
    content = resp.choices[0].message.content
    if not content:
        raise LLMCallError("empty LLM response content")
    return str(content)


def _call_raw(messages: list[dict[str, str]], max_tokens: int, temperature: float) -> str:
    """
    Tries every available Gemini key in the fallback pool (advanced/src/harness/keys.py)
    before giving up -- a key whose free-tier quota is exhausted (per-minute or per-day,
    distinguished by the error text) is marked and skipped for the rest of that cooldown
    window, and the next key is tried immediately. Non-Gemini models (no key pool
    configured) fall back to a single call using litellm's normal env-var resolution.
    """
    import litellm

    if not _IS_GEMINI or not _keys.has_any_key():
        return _call_one(messages, max_tokens, temperature, api_key=None)

    last_err: Exception | None = None
    attempts = 0
    max_attempts = max(len(_keys.all_keys()) * 2, 1)
    while attempts < max_attempts:
        key = _keys.next_key()
        if key is None:
            break
        attempts += 1
        try:
            return _call_one(messages, max_tokens, temperature, api_key=key)
        except litellm.RateLimitError as e:  # type: ignore[attr-defined]
            last_err = e
            _keys.mark_exhausted(key, str(e))
            continue
    raise last_err or LLMCallError("no Gemini API keys available (all exhausted or none configured)")


def _repair_truncated_json(fragment: str) -> dict[str, Any] | None:
    """
    Best-effort recovery for a JSON object cut off mid-string by a max_tokens limit,
    e.g. '{"supported": true, "confidence": 0.8, "concern": "The contract specifies'.
    Closes the open string and any open braces, then tries to parse. Returns None if
    the fragment isn't recoverable this way (caller then surfaces the original error).
    """
    frag = fragment.strip()
    if not frag.startswith("{"):
        return None
    # If truncated inside an open string literal (odd number of unescaped quotes), close it.
    unescaped_quotes = len(re.findall(r'(?<!\\)"', frag))
    if unescaped_quotes % 2 == 1:
        frag += '"'
    open_braces = frag.count("{") - frag.count("}")
    frag += "}" * max(open_braces, 0)
    try:
        result: dict[str, Any] = json.loads(frag)
        return result
    except json.JSONDecodeError:
        return None


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first {...} JSON object out of an LLM response (tolerates markdown code fences)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*)\s*```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        parsed: dict[str, Any] = json.loads(match.group(0))
        return parsed
    # No balanced object found -- likely truncated by max_tokens. Try to repair.
    open_match = re.search(r"\{.*", text, flags=re.DOTALL)
    if open_match:
        repaired = _repair_truncated_json(open_match.group(0))
        if repaired is not None:
            logger.warning("recovered truncated JSON from LLM response (%d chars)", len(text))
            return repaired
    raise ValueError(f"no JSON object found in LLM response: {text[:200]!r}")


def call_llm_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 900,
    temperature: float = 0.0,
    mock_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call the LLM, parse a JSON object out of the reply, and return it.

    Never raises: on any failure (no key, network error, bad JSON) returns
    mock_response (or {} if none given) with "_mock": True and "_error" set,
    so callers can degrade gracefully instead of crashing the harness.
    """
    t0 = time.perf_counter()
    base = dict(mock_response or {})
    if not llm_available():
        logger.info("llm unavailable (EVAL_MOCK or no key) -- using mock_response, model=%s", LLM_MODEL)
        return {**base, "_mock": True, "_ran": False}
    try:
        content = _call_raw(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        parsed = _extract_json(content)
        parsed["_mock"] = False
        parsed["_ran"] = True
        parsed["_latency_ms"] = int((time.perf_counter() - t0) * 1000)
        parsed["_model"] = LLM_MODEL
        return parsed
    except Exception as e:  # noqa - any failure degrades to mock, never crashes the caller
        logger.warning("call_llm_json failed for model=%s: %s -- falling back to mock", LLM_MODEL, e)
        return {**base, "_mock": True, "_ran": False, "_error": f"{type(e).__name__}: {e}"}
