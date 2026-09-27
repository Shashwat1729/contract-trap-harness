"""
BM25 lexical hybrid layer -- a free, deterministic, always-available third signal
alongside extract.py's regex layer and semantic.py's real-embedding layer.

Why this exists: semantic.py's embedding layer is real signal (CHANGELOG #13) but
depends on a paid, quota-limited API that has repeatedly gone dark mid-evaluation in
this project (CHANGELOG #13/#14/#18 -- free-tier per-minute and per-day caps). BM25
(Robertson & Zaragoza, Okapi BM25) is a classical sparse lexical-overlap ranking
function: pure term-frequency/inverse-document-frequency statistics, no network call,
no API key, no quota. It runs over the exact same real CUAD category-description
anchor text semantic.py already uses (data/clause_anchors.json's "texts" field, built
from CUAD's own official category descriptions -- see scripts/build_semantic_anchors.py)
so it introduces no new gold-label leakage risk: the anchor text is the category
DEFINITION, not a labeled example from the 510-contract eval set.

It catches lexical-overlap paragraphs regex's fixed pattern set missed but that don't
need a full embedding call to recognize -- e.g. "notice of its intention not to renew
this agreement" scoring high against the "Notice Period to Terminate Renewal" anchor
description by shared vocabulary alone, with zero API cost.

Known characteristic, not a bug: rank_bm25's IDF statistics need a handful of documents
to be meaningful -- a per-contract candidate pool of only 1-2 paragraphs can score every
query as 0.0 (verified: real contracts' typical candidate counts, dozens of un-matched
paragraphs per document, do not hit this; the full-510-contract sweep in
scripts/tune_bm25_threshold.py produced real, monotonic, non-degenerate score
distributions). The safe failure mode either way is silently scoring low and never
clearing threshold, not a wrong/garbage hit -- consistent with every other layer in this
module degrading gracefully rather than raising.

Because this needs zero API budget, its threshold is tuned against the FULL 510-real-
contract CUAD set, not a small quota-limited dev sample the way semantic.py's
DEFAULT_THRESHOLD had to be (n=7, see CHANGELOG #13) -- see
scripts/tune_bm25_threshold.py and DEFAULT_THRESHOLD's own comment below for the real
sweep result this value came from.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from .extract import ClauseHit, SAAS_TYPES, _extract_snippet
from .ingest import Page, offset_to_page_line
from .semantic import _chunk_candidates, _load_anchors

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Tuned against the FULL 510 real CUAD contracts (this layer is $0/deterministic, so
# -- unlike semantic.py's n=7 embedding threshold, quota-limited to a tiny dev sample
# -- there was no reason to settle for a small-sample estimate). scripts/
# tune_bm25_threshold.py --sample 0 swept 2-100; the best-F1 point (threshold=10) trades
# too much precision for this project's stated "high precision, conservative recall"
# profile (recall 37.5%->71.2% but precision 92.8%->61.2% on that script's own,
# slightly different rule accounting -- see its docstring). 42.0 was chosen instead as
# the precision-preserving point: recall +4.9pp, precision -5.1pp in that same sweep's
# accounting. See CHANGELOG #19 for the real, canonical (11-rule, eval_cuad_ground_
# truth.py-consistent) full-510 number this layer produces when enabled.
DEFAULT_THRESHOLD = 42.0


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bm25_candidates(
    contract_text: str,
    pages: list[Page],
    existing_hits: list[ClauseHit],
) -> list[tuple[int, int, str, str, float]]:
    """
    Scores paragraphs regex missed against every clause type's real CUAD-description
    anchor text via BM25 lexical overlap. Returns raw (start, end, text,
    best_clause_type, best_bm25_score) tuples for EVERY candidate, unfiltered by
    threshold -- callers (bm25_hits(), or a threshold sweep) decide the cutoff.
    Returns [] (never raises) if no candidates or anchors are available. Never touches
    the network -- this is pure local computation, always available regardless of
    API key / quota state.
    """
    anchors = _load_anchors()
    if not anchors:
        return []
    covered = [(h.start, h.end) for h in existing_hits]
    candidates = _chunk_candidates(contract_text, covered)
    if not candidates:
        return []

    corpus_tokens = [_tokenize(c[2]) for c in candidates]
    if not any(corpus_tokens):
        return []
    bm25 = BM25Okapi(corpus_tokens)

    best_type: list[str | None] = [None] * len(candidates)
    best_score = [0.0] * len(candidates)
    for ctype in SAAS_TYPES:
        anchor = anchors.get(ctype)
        if not anchor:
            continue
        query_tokens: list[str] = []
        for t in anchor.get("texts", []):
            query_tokens.extend(_tokenize(t))
        if not query_tokens:
            continue
        scores = bm25.get_scores(query_tokens)
        for i, score in enumerate(scores):
            if score > best_score[i]:
                best_score[i] = float(score)
                best_type[i] = ctype

    out: list[tuple[int, int, str, str, float]] = []
    for (start, end, text), btype, bscore in zip(candidates, best_type, best_score):
        if btype is not None:
            out.append((start, end, text, btype, bscore))
    return out


def bm25_hits(
    contract_text: str,
    pages: list[Page],
    existing_hits: list[ClauseHit],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[ClauseHit]:
    """
    Additive lexical pass: scores paragraphs regex missed against real CUAD category
    descriptions via BM25, flags any whose best score clears `threshold`. $0, no
    network call, always available -- degrades to [] only if the anchor data file is
    missing, never due to API/quota state.
    """
    candidates = bm25_candidates(contract_text, pages, existing_hits)
    hits: list[ClauseHit] = []
    for start, end, text, best_type, best_score in candidates:
        if best_score < threshold:
            continue
        page, line = offset_to_page_line(start, pages, contract_text)
        snippet = _extract_snippet(contract_text, start, end)
        # BM25 scores are unbounded (grow with term overlap/rarity, not a 0-1
        # cosine), so confidence is a coarse rank-based estimate, not a probability.
        conf = round(min(0.5 + min(best_score / (threshold * 2), 1.0) * 0.4, 0.9), 3)
        hits.append(ClauseHit(
            clause_type=best_type,
            span_text=snippet,
            start=start, end=end,
            page=page, line=line,
            confidence=conf,
            match_kind="bm25",
        ))
    return hits
