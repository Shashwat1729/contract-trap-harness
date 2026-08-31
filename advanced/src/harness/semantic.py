"""
Semantic clause retrieval -- hybrid augmentation on top of extract.py's regex layer.

Real embeddings (advanced/src/harness/embed.py, gemini-embedding-001) against real
anchor text (advanced/src/harness/data/clause_anchors.json, built from CUAD's own
official category descriptions -- see scripts/build_semantic_anchors.py), not a
hand-rolled string-similarity heuristic. This exists because extract.py's regex
patterns have a real, disclosed recall ceiling: real contracts phrase clauses in ways
no fixed pattern set fully enumerates. Semantic similarity catches meaning-matches
regex misses; regex stays primary because it's free, instant, and near-perfect
precision once broadened -- this module is additive recall, not a replacement.

Only paragraphs NOT already covered by a regex hit are embedded, so this never
duplicates what extract.py already found, and API cost scales with what regex
*missed*, not with document length.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .embed import embed_available, embed_texts
from .extract import ClauseHit, SAAS_TYPES, _extract_snippet
from .ingest import Page, offset_to_page_line

logger = logging.getLogger("advanced.harness.semantic")

_ANCHORS_PATH = Path(__file__).parent / "data" / "clause_anchors.json"
_anchors_cache: dict[str, dict[str, Any]] | None = None

# Candidate paragraphs are chunked, not embedded sentence-by-sentence: keeps the
# number of real API calls bounded (roughly proportional to document sections, not
# document length) while still giving each embedding enough context to be meaningful.
_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")
_MIN_CHUNK_CHARS = 40
_MAX_CHUNK_CHARS = 600
_MAX_CANDIDATES_PER_DOC = 120

# PRELIMINARY -- picked from scripts/tune_semantic_threshold.py's real-API sweep, but
# on a real free-tier daily-quota-limited sample of only 7 CUAD dev contracts (see
# CHANGELOG #13): at 0.65, recall rose 45.5% -> 52.3% (+6.8pp) vs regex-only with
# precision 74.2% (down from regex's 100% on that same tiny sample). That is a real
# signal from real embeddings and real CUAD labels, not a synthetic estimate -- but
# n=7 is too small to call this threshold settled. Re-run
# `python scripts/tune_semantic_threshold.py --dev-size 40` once daily embedding
# quota resets and update this value from that larger sweep before treating it as
# final.
DEFAULT_THRESHOLD = 0.65


def _load_anchors() -> dict[str, dict[str, Any]]:
    global _anchors_cache
    if _anchors_cache is None:
        if not _ANCHORS_PATH.exists():
            logger.warning("clause_anchors.json not found at %s -- run scripts/build_semantic_anchors.py", _ANCHORS_PATH)
            _anchors_cache = {}
        else:
            _anchors_cache = json.loads(_ANCHORS_PATH.read_text(encoding="utf-8"))
    return _anchors_cache


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))


def _chunk_candidates(contract_text: str, covered: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    """Paragraph-level chunks not overlapping any already-covered (regex-hit) span."""
    chunks: list[tuple[int, int, str]] = []
    pos = 0
    for m in _PARA_SPLIT_RE.finditer(contract_text):
        para = contract_text[pos : m.start()]
        para_start = pos
        pos = m.end()
        text = para.strip()
        if len(text) < _MIN_CHUNK_CHARS:
            continue
        start = para_start + para.find(text[0]) if text else para_start
        end = start + len(text)
        if any(start < c_end and end > c_start for c_start, c_end in covered):
            continue
        chunks.append((start, end, text[:_MAX_CHUNK_CHARS]))
    tail = contract_text[pos:].strip()
    if len(tail) >= _MIN_CHUNK_CHARS:
        start = pos + contract_text[pos:].find(tail[0])
        end = start + len(tail)
        if not any(start < c_end and end > c_start for c_start, c_end in covered):
            chunks.append((start, end, tail[:_MAX_CHUNK_CHARS]))
    return chunks[:_MAX_CANDIDATES_PER_DOC]


def semantic_candidates(
    contract_text: str,
    pages: list[Page],
    existing_hits: list[ClauseHit],
) -> list[tuple[int, int, str, str, float]]:
    """
    Embeds paragraphs regex missed and scores each against every clause type's
    anchor set. Returns raw (start, end, text, best_clause_type, best_cosine_score)
    tuples for EVERY candidate, unfiltered by threshold -- callers (semantic_hits(),
    or a threshold sweep) decide the cutoff. Returns [] (never raises) if embeddings
    are unavailable.
    """
    if not embed_available():
        return []
    anchors = _load_anchors()
    if not anchors:
        return []

    covered = [(h.start, h.end) for h in existing_hits]
    candidates = _chunk_candidates(contract_text, covered)
    if not candidates:
        return []

    texts = [c[2] for c in candidates]
    embeddings = embed_texts(texts)
    if embeddings is None:
        return []

    out: list[tuple[int, int, str, str, float]] = []
    for (start, end, text), emb in zip(candidates, embeddings):
        best_type, best_score = None, 0.0
        for ctype in SAAS_TYPES:
            anchor = anchors.get(ctype)
            if not anchor:
                continue
            score = max(_cosine(emb, a) for a in anchor["embeddings"])
            if score > best_score:
                best_type, best_score = ctype, score
        if best_type is not None:
            out.append((start, end, text, best_type, best_score))
    return out


def semantic_hits(
    contract_text: str,
    pages: list[Page],
    existing_hits: list[ClauseHit],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[ClauseHit]:
    """
    Additive semantic pass: embeds paragraphs regex missed, flags any whose
    embedding is close enough to a clause type's real CUAD-description anchor.
    Returns [] (never raises) if embeddings are unavailable -- callers should treat
    that as "semantic layer skipped," not an error; extract_clauses_hybrid() already
    does this.
    """
    candidates = semantic_candidates(contract_text, pages, existing_hits)
    hits: list[ClauseHit] = []
    for start, end, text, best_type, best_score in candidates:
        if best_score < threshold:
            continue
        page, line = offset_to_page_line(start, pages, contract_text)
        snippet = _extract_snippet(contract_text, start, end)
        hits.append(ClauseHit(
            clause_type=best_type,
            span_text=snippet,
            start=start, end=end,
            page=page, line=line,
            confidence=round(min(0.5 + best_score * 0.5, 0.9), 3),
            match_kind="semantic",
        ))
    return hits
