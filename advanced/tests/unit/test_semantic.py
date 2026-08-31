"""
Unit tests for the semantic layer (advanced/src/harness/semantic.py) -- mocked
embeddings only, no real API calls / no quota spend. Real-API validation lives in
scripts/tune_semantic_threshold.py and eval_cuad_ground_truth.py --hybrid, run
manually against live quota (see CHANGELOG #13).
"""
from __future__ import annotations

import pytest

from advanced.src.harness import semantic as sem
from advanced.src.harness.extract import ClauseHit
from advanced.src.harness.ingest import Page


def _fake_anchors():
    return {
        "Non-Compete": {"texts": ["Non-Compete"], "embeddings": [[1.0, 0.0, 0.0]]},
        "Audit Rights": {"texts": ["Audit Rights"], "embeddings": [[0.0, 1.0, 0.0]]},
    }


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    monkeypatch.setattr(sem, "_anchors_cache", None)
    yield
    sem._anchors_cache = None


def test_semantic_hits_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(sem, "embed_available", lambda: False)
    text = "Section 1.\n\nThe supplier shall not compete with the customer in any territory.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    assert sem.semantic_hits(text, pages, []) == []


def test_semantic_hits_flags_close_match(monkeypatch):
    monkeypatch.setattr(sem, "embed_available", lambda: True)
    monkeypatch.setattr(sem, "_load_anchors", _fake_anchors)

    text = "PARA ONE TEXT HERE PADDING TO MEET MIN CHUNK LENGTH REQUIREMENT.\n\nPARA TWO TEXT HERE ALSO PADDED OUT LONG ENOUGH TO COUNT AS A CANDIDATE CHUNK.\n"

    def fake_embed_texts(texts, batch_size=100):
        # first paragraph embeds close to "Non-Compete", second close to nothing
        return [[0.9, 0.1, 0.0], [0.0, 0.0, 1.0]]

    monkeypatch.setattr(sem, "embed_texts", fake_embed_texts)
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    hits = sem.semantic_hits(text, pages, [], threshold=0.5)

    assert len(hits) == 1
    assert hits[0].clause_type == "Non-Compete"
    assert hits[0].match_kind == "semantic"
    assert 0.5 <= hits[0].confidence <= 0.9


def test_semantic_hits_skips_regex_covered_spans(monkeypatch):
    monkeypatch.setattr(sem, "embed_available", lambda: True)
    monkeypatch.setattr(sem, "_load_anchors", _fake_anchors)
    calls = []

    def fake_embed_texts(texts, batch_size=100):
        calls.append(texts)
        return [[0.9, 0.1, 0.0] for _ in texts]

    monkeypatch.setattr(sem, "embed_texts", fake_embed_texts)

    text = "ONLY PARAGRAPH HERE PADDED OUT LONG ENOUGH TO COUNT AS A REAL CANDIDATE CHUNK FOR THIS TEST.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    existing = [ClauseHit(clause_type="Audit Rights", span_text=text, start=0, end=len(text), page=1, line=1, confidence=0.8, match_kind="pattern")]

    hits = sem.semantic_hits(text, pages, existing, threshold=0.5)
    assert hits == []
    assert calls == []  # no candidates left to embed -- the whole paragraph was already covered


def test_semantic_candidates_returns_raw_scores_unfiltered(monkeypatch):
    monkeypatch.setattr(sem, "embed_available", lambda: True)
    monkeypatch.setattr(sem, "_load_anchors", _fake_anchors)
    monkeypatch.setattr(sem, "embed_texts", lambda texts, batch_size=100: [[0.1, 0.1, 0.1] for _ in texts])

    text = "SOME PARAGRAPH TEXT PADDED OUT LONG ENOUGH TO COUNT AS A CANDIDATE CHUNK FOR THIS UNIT TEST.\n"
    pages = [Page(num=1, text=text, start=0, end=len(text))]
    candidates = sem.semantic_candidates(text, pages, [])

    assert len(candidates) == 1
    _start, _end, _text, best_type, best_score = candidates[0]
    assert best_type in ("Non-Compete", "Audit Rights")
    assert 0.0 < best_score < 1.0  # low-similarity fake embedding, returned unfiltered
