"""
Unit tests for the LLM-as-generator layer (advanced/src/harness/llm_extract.py) --
mocked LLM calls only, no real API spend. Real-API validation is manual (small,
capped by LLM_EXTRACT_MAX_CALLS) -- see CHANGELOG #22.
"""
from __future__ import annotations

from advanced.src.harness import llm_extract as le
from advanced.src.harness.extract import ClauseHit
from advanced.src.harness.ingest import Page


def _page(text: str) -> list[Page]:
    return [Page(num=1, text=text, start=0, end=len(text))]


def test_unavailable_returns_empty(monkeypatch):
    monkeypatch.setattr(le, "llm_available", lambda: False)
    text = "Some contract text with no matching clauses."
    assert le.llm_extract_missing_clauses(text, _page(text), []) == []


def test_no_missing_types_skips_call_entirely(monkeypatch):
    monkeypatch.setattr(le, "llm_available", lambda: True)
    calls = {"n": 0}

    def _fake_call(*a, **kw):
        calls["n"] += 1
        return {"_ran": True, "found": False, "span": ""}

    monkeypatch.setattr(le, "call_llm_json", _fake_call)
    text = "irrelevant"
    existing = [
        ClauseHit(clause_type=ct, span_text="x", start=0, end=1, page=1, line=1, confidence=0.8, match_kind="pattern")
        for ct in le._target_clause_types()
    ]
    assert le.llm_extract_missing_clauses(text, _page(text), existing) == []
    assert calls["n"] == 0


def test_verbatim_span_accepted_and_located(monkeypatch):
    monkeypatch.setattr(le, "llm_available", lambda: True)
    text = (
        "Section 1. Renewal Term. This Agreement shall automatically renew for successive "
        "twenty-four (24) month periods unless either party provides notice.\n\n"
        "Section 2. Unrelated boilerplate about payment terms and invoicing schedules follows here.\n"
    )
    real_span = "This Agreement shall automatically renew for successive twenty-four (24) month periods unless either party provides notice."

    def _fake_call(system, user, **kw):
        if "Renewal Term" in user:
            return {"_ran": True, "found": True, "span": real_span}
        return {"_ran": True, "found": False, "span": ""}

    monkeypatch.setattr(le, "call_llm_json", _fake_call)
    monkeypatch.setattr(le, "_target_clause_types", lambda: ["Renewal Term"])
    hits = le.llm_extract_missing_clauses(text, _page(text), [])
    assert len(hits) == 1
    h = hits[0]
    assert h.clause_type == "Renewal Term"
    assert h.match_kind == "llm_generated"
    assert real_span in text[h.start:h.end] or real_span.lower() in h.span_text.lower()
    assert h.confidence == le.LLM_EXTRACT_CONFIDENCE


def test_hallucinated_span_discarded(monkeypatch):
    """A span the LLM claims exists but does NOT appear verbatim in the contract must
    never become a ClauseHit -- this is the core anti-hallucination guarantee."""
    monkeypatch.setattr(le, "llm_available", lambda: True)
    text = "Section 1. This document contains only unrelated payment and invoicing terms.\n"

    def _fake_call(system, user, **kw):
        return {"_ran": True, "found": True, "span": "Either party may terminate for convenience on thirty days written notice."}

    monkeypatch.setattr(le, "call_llm_json", _fake_call)
    monkeypatch.setattr(le, "_target_clause_types", lambda: ["Termination for Convenience"])
    hits = le.llm_extract_missing_clauses(text, _page(text), [])
    assert hits == []


def test_max_calls_caps_number_of_llm_invocations(monkeypatch):
    monkeypatch.setattr(le, "llm_available", lambda: True)
    calls = {"n": 0}

    def _fake_call(system, user, **kw):
        calls["n"] += 1
        return {"_ran": True, "found": False, "span": ""}

    monkeypatch.setattr(le, "call_llm_json", _fake_call)
    text = "irrelevant text with nothing to find"
    hits = le.llm_extract_missing_clauses(text, _page(text), [], max_calls=2)
    assert hits == []
    assert calls["n"] == 2


def test_find_verbatim_exact_match():
    text = "The quick brown fox jumps over the lazy dog."
    located = le._find_verbatim(text, "brown fox jumps")
    assert located is not None
    start, end = located
    assert text[start:end] == "brown fox jumps"


def test_find_verbatim_not_present_returns_none():
    text = "The quick brown fox jumps over the lazy dog."
    assert le._find_verbatim(text, "a completely unrelated sentence never in the text") is None


def test_find_verbatim_normalized_fallback_anchors_to_correct_occurrence_not_first():
    """
    Regression test for a real bug a strict-judge audit found (CHANGELOG #22): the
    normalized-fallback path used to locate the real offset by taking the FIRST
    occurrence anywhere in the document of the span's first 5 words, after only
    checking the normalized span existed SOMEWHERE in the document -- not
    necessarily at that first occurrence. A document whose opening boilerplate
    happens to repeat the exact same 5-word opener before the real (whitespace-
    mangled) clause could anchor to the wrong, unrelated location and still
    report a "verified" match. This fixture puts the IDENTICAL 5-word opener
    ("This Agreement shall provide for") at TWO locations that then diverge: an
    unrelated decoy occurrence, and the real target occurrence (with a
    mid-sentence linebreak right after "for" that the LLM's own span doesn't
    have, forcing the whitespace-tolerant anchor path). The located offset must
    point at the SECOND (real, matching) occurrence, not the decoy.
    """
    decoy = "This Agreement shall provide for a completely different administrative purpose entirely.\n\n"
    real = "This Agreement shall provide for\nautomatic renewal on a twelve month basis unless terminated."
    text = decoy + real
    span = "This Agreement shall provide for automatic renewal on a twelve month basis unless terminated."
    located = le._find_verbatim(text, span)
    assert located is not None
    start, end = located
    assert start == text.index(real)  # anchored to the REAL occurrence, not the decoy at offset 0
    assert le._normalize(text[start:end]).startswith(le._normalize(span))
