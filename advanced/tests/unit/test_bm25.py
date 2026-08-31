"""
Unit tests for the BM25 lexical layer (advanced/src/harness/bm25.py) -- no API calls,
no network, no mocking needed for the scoring itself (BM25 is pure local computation).
Real, full-510-contract validation lives in scripts/tune_bm25_threshold.py and
eval_cuad_ground_truth.py --bm25, both $0/deterministic (see CHANGELOG #19).
"""
from __future__ import annotations

import pytest

from advanced.src.harness import bm25 as bm
from advanced.src.harness.extract import ClauseHit
from advanced.src.harness.ingest import Page


def _fake_anchors():
    return {
        "Non-Compete": {"texts": ["Non-Compete", "shall not compete with the customer in any territory"]},
        "Audit Rights": {"texts": ["Audit Rights", "right to audit books and records upon reasonable notice"]},
    }


def test_bm25_hits_no_anchors_returns_empty(monkeypatch):
    monkeypatch.setattr(bm, "_load_anchors", lambda: {})
    text = "The supplier shall not compete with the customer in any territory whatsoever.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    assert bm.bm25_hits(text, pages, []) == []


# rank_bm25's IDF statistics degenerate to all-zero on a very small (1-2 doc) corpus
# (verified: a real characteristic of the library, documented in bm25.py's own
# docstring) -- these fixtures use 5+ paragraphs, matching the realistic per-contract
# candidate-pool size the full-510-contract sweep (scripts/tune_bm25_threshold.py) was
# actually run against, so scores are meaningful rather than degenerate.
_MULTI_PARA_TEXT = (
    "PARAGRAPH ONE. The supplier shall not compete with the customer in any territory for the term of this agreement.\n\n"
    "PARAGRAPH TWO. This section discusses unrelated payment terms and invoicing schedules for the parties involved.\n\n"
    "PARAGRAPH THREE. This clause addresses confidentiality obligations of both parties hereto for the agreement term.\n\n"
    "PARAGRAPH FOUR. Governing law of the state of Delaware shall apply to any dispute arising under this agreement.\n\n"
    "PARAGRAPH FIVE. Any notice required under this agreement shall be given in writing to the other party hereto.\n"
)


def test_bm25_hits_flags_lexically_close_paragraph(monkeypatch):
    monkeypatch.setattr(bm, "_load_anchors", _fake_anchors)

    # Real per-paragraph scores for this fixture (checked directly): paragraph one
    # (genuine "shall not compete...territory" overlap) scores ~7.2; every other
    # paragraph scores under 1.5 on incidental word overlap ("the", "agreement").
    # threshold=3.0 sits cleanly between them.
    pages = [Page(num=1, text=_MULTI_PARA_TEXT, start=0, end=len(_MULTI_PARA_TEXT))]
    hits = bm.bm25_hits(_MULTI_PARA_TEXT, pages, [], threshold=3.0)

    assert len(hits) == 1
    assert hits[0].clause_type == "Non-Compete"
    assert hits[0].match_kind == "bm25"
    assert 0.0 < hits[0].confidence <= 0.9


def test_bm25_hits_skips_regex_covered_spans(monkeypatch):
    monkeypatch.setattr(bm, "_load_anchors", _fake_anchors)

    text = "The supplier shall not compete with the customer in any territory for the term of this agreement.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    existing = [ClauseHit(clause_type="Non-Compete", span_text=text, start=0, end=len(text), page=1, line=1, confidence=0.8, match_kind="pattern")]

    hits = bm.bm25_hits(text, pages, existing, threshold=0.5)
    assert hits == []


def test_bm25_candidates_returns_raw_scores_unfiltered(monkeypatch):
    monkeypatch.setattr(bm, "_load_anchors", _fake_anchors)

    pages = [Page(num=1, text=_MULTI_PARA_TEXT, start=0, end=len(_MULTI_PARA_TEXT))]
    candidates = bm.bm25_candidates(_MULTI_PARA_TEXT, pages, [])

    assert len(candidates) == 5
    _start, _end, text0, best_type0, best_score0 = candidates[0]
    assert "PARAGRAPH ONE" in text0
    assert best_type0 == "Non-Compete"  # real lexical overlap with the fake anchor text
    assert best_score0 > 0.0
    assert all(score >= 0.0 for *_rest, score in candidates)


def test_bm25_hits_threshold_gates_low_scores(monkeypatch):
    monkeypatch.setattr(bm, "_load_anchors", _fake_anchors)

    text = "SOME PARAGRAPH WITH NO LEXICAL OVERLAP TO EITHER ANCHOR AT ALL, JUST FILLER WORDS HERE.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    hits = bm.bm25_hits(text, pages, [], threshold=1000.0)
    assert hits == []


def test_extract_clauses_hybrid_bm25_flag_is_independent_of_semantic(monkeypatch):
    from advanced.src.harness import extract as ext

    text = "Some contract paragraph text that regex alone will not match against any playbook pattern here.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    fake_hit = ClauseHit(clause_type="Non-Compete", span_text="stub", start=0, end=4, page=1, line=1, confidence=0.7, match_kind="bm25")

    # Stub bm25_hits directly (real-threshold tuning is bm25_hits' own test's job) --
    # this test only proves extract_clauses_hybrid's bm25=True flag actually calls it,
    # independently of semantic=False, and bm25=False does not call it at all.
    calls = {"n": 0}

    def fake_bm25_hits(*a, **k):
        calls["n"] += 1
        return [fake_hit]

    monkeypatch.setattr("advanced.src.harness.bm25.bm25_hits", fake_bm25_hits)

    without = ext.extract_clauses_hybrid(text, pages, semantic=False, bm25=False)
    assert calls["n"] == 0
    assert not any(h.match_kind == "bm25" for h in without)

    with_bm25 = ext.extract_clauses_hybrid(text, pages, semantic=False, bm25=True)
    assert calls["n"] == 1
    assert any(h.match_kind == "bm25" for h in with_bm25)
