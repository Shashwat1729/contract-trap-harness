"""
LLM-as-generator: an opt-in pass that proposes candidate clauses for playbook rule
types the deterministic regex/semantic/BM25 layers found ZERO hits for, instead of
only ever filtering/scoring what those layers already proposed.

Why this exists: a strict-judge audit of this project (CHANGELOG #21/#22) flagged
that every real LLM call in the harness (`llm_verify.py`, `llm_verify.llm_verify_finding`)
only ever judges a candidate someone else already proposed -- it never originates one.
`coverage_gaps` (core.py) already surfaces "this rule has zero hits" but only as a
non-actionable checklist flag for a single hardcoded rule (P-03), never turned into
an actual evidence-gated finding. This module closes that gap for EVERY playbook rule.

Critical design constraint -- this must never become a hallucination bypass: the LLM
is asked ONLY to locate a verbatim excerpt, never to describe or paraphrase one. Any
returned span that is not found as an exact (whitespace-normalized, case-insensitive)
substring of the real contract text is discarded before it ever becomes a ClauseHit.
A hit that survives this check is then run through the EXACT SAME downstream pipeline
as any regex/semantic/BM25 hit -- assess_risk's deterministic per-clause-type trap
logic, then dual_verify_finding's own independent span-in-contract check, then
(if enabled) llm_verify_finding's second-opinion cross-check -- so a hallucinated or
mischaracterized span can be caught at up to three further independent gates even if
this module's own check somehow missed it. Nothing here can inject an approved finding
without evidence; at worst it wastes a call finding nothing.

Cost control ("small/cheap", per the standing instruction): capped at
LLM_EXTRACT_MAX_CALLS calls per document (default 6). There are 12 playbook rules
across 12 distinct clause types (two rules, P-04 and P-12, both apply to "Cap on
Liability"/"Limitation of Liability" -- everything else is a 1:1 rule:type mapping)
-- the default cap does NOT cover a hypothetical fully-empty document (it would
silently generate candidates for only the first 6 missing types, in playbook order,
and leave the rest with none); it is sized for the realistic case, where a real
contract is missing only a handful of clause types and costs 1 call per missing
type, not 12. Off by default (ENABLE_LLM_EXTRACT=0),
same opt-in pattern as ENABLE_SEMANTIC_EXTRACTION/ENABLE_BM25_EXTRACTION. Degrades to
a no-op with EVAL_MOCK=1 or no provider key, exactly like llm_verify.py -- offline
reproduction is unaffected.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .extract import ClauseHit, _extract_snippet
from .ingest import Page, offset_to_page_line
from .llm import call_llm_json, llm_available
from .risk import PLAYBOOK

logger = logging.getLogger("advanced.harness.llm_extract")

_ANCHORS_PATH = Path(__file__).parent / "data" / "clause_anchors.json"
_descriptions_cache: dict[str, str] | None = None

SYSTEM_PROMPT = (
    "You are a precise contract-clause locator. You are given the full text of a "
    "contract and asked whether it contains a clause of one specific type. You must "
    "NEVER paraphrase, summarize, or invent text. If the clause type genuinely exists "
    "in the document, copy the exact verbatim sentence(s) that constitute it -- "
    "character-for-character as written, at most 400 characters -- into \"span\". If "
    "it does not exist anywhere in the document, set \"found\" to false and \"span\" "
    "to an empty string. Reply with ONLY a single JSON object, no prose, no markdown "
    'fence:\n{"found": true|false, "span": "<verbatim excerpt or empty string>"}'
)

# Confidence for an LLM-generated hit is deliberately lower than a regex hit's
# baseline (0.7-0.9) and roughly in line with the semantic layer's calibration
# (semantic.py: 0.5-0.9 scaled by cosine score) -- an LLM-located span has passed
# an exact-substring check (so it is genuinely IN the document) but has not been
# confirmed as the CORRECT clause type the way a hand-written regex pattern has.
LLM_EXTRACT_CONFIDENCE = 0.55


def _load_descriptions() -> dict[str, str]:
    """CUAD official category descriptions, same source file semantic.py's anchors
    use -- texts[1] is the long-form description, texts[0] is just the bare label."""
    global _descriptions_cache
    if _descriptions_cache is not None:
        return _descriptions_cache
    try:
        if not _ANCHORS_PATH.exists():
            _descriptions_cache = {}
            return _descriptions_cache
        raw = json.loads(_ANCHORS_PATH.read_text(encoding="utf-8"))
        out: dict[str, str] = {}
        for ctype, entry in raw.items():
            texts = entry.get("texts") or []
            out[ctype] = texts[1] if len(texts) > 1 else (texts[0] if texts else ctype)
        _descriptions_cache = out
    except Exception as e:
        logger.warning("_load_descriptions failed, falling back to bare labels: %s", e)
        _descriptions_cache = {}
    return _descriptions_cache


def _target_clause_types() -> list[str]:
    """All distinct clause types any playbook rule cares about, in playbook order,
    deduplicated -- these are the only types worth spending a call asking about."""
    seen: set[str] = set()
    out: list[str] = []
    for rule in PLAYBOOK.values():
        for ctype in rule["clause_types"]:
            if ctype not in seen:
                seen.add(ctype)
                out.append(ctype)
    return out


def _normalize(s: str) -> str:
    return " ".join(s.split()).lower()


def _find_verbatim(contract_text: str, span: str) -> tuple[int, int] | None:
    """
    Locate `span` as a genuine substring of contract_text. Tries an exact
    case-insensitive match first; falls back to a whitespace-tolerant search (LLMs
    sometimes collapse a mid-sentence linebreak) in which every token of the span must
    appear in order, separated only by whitespace, at one real location.

    History: an earlier version anchored on the FIRST occurrence of the span's first 5
    words anywhere in the document after only confirming the normalized span existed
    SOMEWHERE -- common opening phrasing ("This Agreement shall...") recurring in an
    unrelated earlier clause made it point at unrelated text (CHANGELOG #22 audit). The
    follow-up verified each anchor occurrence but still estimated the end offset as
    start + len(span) + 40. The token regex returns the true matched [start, end).

    Returns None (never raises) if no genuine, verified match is found --
    callers MUST discard the candidate in that case, never fabricate offsets.
    """
    if not span or not span.strip():
        return None
    lo_text = contract_text.lower()
    lo_span = span.lower().strip()
    idx = lo_text.find(lo_span)
    if idx != -1 and len(lo_text) == len(contract_text):  # lower() kept offsets aligned
        return idx, idx + len(lo_span)
    norm_span = _normalize(span)
    if len(norm_span) < 15:
        return None
    # Whitespace-TOLERANT, token-exact search: every token of the span must appear in
    # order, separated only by whitespace (a linebreak where the LLM wrote a space, or
    # vice versa). Each match is a genuine location in the real text, and its end offset
    # is the real end of the matched text -- not an estimate.
    pattern = re.compile(r"\s+".join(re.escape(tok) for tok in span.split()), re.IGNORECASE)
    m = pattern.search(contract_text)
    if m is None:
        return None
    return m.start(), m.end()


def llm_extract_missing_clauses(
    contract_text: str,
    pages: list[Page],
    existing_hits: list[ClauseHit],
    max_calls: int = 6,
) -> list[ClauseHit]:
    """
    Additive generator pass: for playbook clause types with ZERO existing hits,
    asks the LLM to locate a verbatim excerpt. Returns [] (never raises) if the
    LLM is unavailable, no clause types are missing, or nothing verifiable is found.
    Every returned ClauseHit has already passed the exact-substring anti-hallucination
    check in _find_verbatim -- it still flows through assess_risk/dual_verify/
    llm_verify exactly like any other hit before it can become an approved finding.
    """
    if not llm_available():
        return []
    present = {h.clause_type for h in existing_hits}
    missing = [ct for ct in _target_clause_types() if ct not in present][:max_calls]
    if not missing:
        return []

    descriptions = _load_descriptions()
    doc_for_prompt = contract_text[:15000]
    hits: list[ClauseHit] = []
    for ctype in missing:
        desc = descriptions.get(ctype, ctype)
        user = (
            f"Clause type to search for: {ctype}\n"
            f"Definition: {desc}\n\n"
            f"Contract text:\n\"\"\"\n{doc_for_prompt}\n\"\"\"\n\n"
            "Does the contract contain a clause of this type? Respond with the JSON "
            "object only."
        )
        mock = {"found": False, "span": ""}
        try:
            result = call_llm_json(SYSTEM_PROMPT, user, max_tokens=700, mock_response=mock)
        except Exception as e:
            logger.warning("llm_extract_missing_clauses call failed for %s: %s", ctype, e)
            continue
        if not result.get("_ran", False) or not result.get("found"):
            continue
        span = str(result.get("span", "") or "")[:400]
        located = _find_verbatim(contract_text, span)
        if located is None:
            logger.warning(
                "llm_extract: discarded unverifiable span for %s (not found verbatim in contract)", ctype
            )
            continue
        start, end = located
        page, line = offset_to_page_line(start, pages, contract_text)
        snippet = _extract_snippet(contract_text, start, end)
        hits.append(ClauseHit(
            clause_type=ctype,
            span_text=snippet,
            start=start, end=end,
            page=page, line=line,
            confidence=LLM_EXTRACT_CONFIDENCE,
            match_kind="llm_generated",
        ))
    return hits
