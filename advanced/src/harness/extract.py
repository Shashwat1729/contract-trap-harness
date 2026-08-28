"""
Extract — clause discovery with CUAD-aware types.

Uses CUAD 41 types filtered to SaaS MSA 12, with span-level citations.
Production: deterministic regex + fuzzy + lexical, then confidence-gated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from .ingest import Page, offset_to_page_line

# CUAD 41 types filtered to SaaS MSA (12) — grounded in handbook + RedlineBench SaaS MSAs
SAAS_TYPES = [
    "Renewal Term",
    "Notice Period to Terminate Renewal",
    "Termination for Convenience",
    "Cap on Liability",
    "Limitation of Liability",
    "Audit Rights",
    "Governing Law",
    "License Grant",
    "Non-Compete",
    "Non-Disparagement",
    "IP Ownership Assignment",
    "Post-Termination Services",
]

# Mapping from clause type -> patterns that indicate that clause's presence
CLAUSE_PATTERNS: dict[str, list[str]] = {
    "Renewal Term": [r"renew(?:al)?\s+term", r"initial\s+term.*renewal", r"auto[\s\-]?renew"],
    "Notice Period to Terminate Renewal": [r"notice\s+period\s+to\s+terminate\s+renewal", r"notice\s+of\s+non[\s\-]?renewal", r"termination\s+notice\s+.*renewal"],
    "Termination for Convenience": [r"termination\s+for\s+convenience", r"terminate\s+for\s+convenience"],
    "Cap on Liability": [r"cap\s+on\s+liability", r"liability\s+cap", r"limitation\s+of\s+liability\s+cap"],
    "Limitation of Liability": [r"limitation\s+of\s+liability", r"limit(?:ation)?\s+of\s+liability", r"liability\s+shall\s+not\s+exceed"],
    "Audit Rights": [r"audit\s+rights?", r"right\s+to\s+audit"],
    "Governing Law": [r"governing\s+law", r"governed\s+by\s+the\s+laws\s+of"],
    "License Grant": [r"license\s+grant", r"grants?\s+to\s+customer\s+a\s+license"],
    "Non-Compete": [r"non[\s\-]?compete", r"covenant\s+not\s+to\s+compete"],
    "Non-Disparagement": [r"non[\s\-]?disparagement", r"shall\s+not\s+disparage"],
    "IP Ownership Assignment": [r"ip\s+ownership\s+assignment", r"assignment\s+of\s+intellectual\s+property"],
    "Post-Termination Services": [r"post[\s\-]?termination\s+services?", r"transition\s+services"],
}

WORD_NUM = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"twenty":20,"twenty-four":24,"twenty four":24,"twenty four months":24}
def parse_months(text: str) -> int | None:
    m = re.search(r"(\d+)\s*months?", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    # word numbers
    low = text.lower()
    for w, val in WORD_NUM.items():
        if w in low and "month" in low:
            return val
    if "one year" in low or "1 year" in low:
        return 12
    if "two years" in low or "2 years" in low:
        return 24
    return None
def parse_days(text: str) -> int | None:
    m = re.search(r"(\d+)\s*days?", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    low = text.lower()
    for w, val in WORD_NUM.items():
        if w in low and "day" in low:
            return val
    return None

TRAP_VALUES: dict[str, dict] = {
    "Renewal Term": {"threshold": 12, "op": "gt", "trap_risk": "High"},
    "Notice Period to Terminate Renewal": {"threshold": 60, "op": "lt", "trap_risk": "High"},
    "Cap on Liability": {"keywords": ["unlimited", "uncapped", "without limitation"], "trap_risk": "High"},
    "Limitation of Liability": {"keywords": ["unlimited", "uncapped"], "trap_risk": "High"},
}


@dataclass
class ClauseHit:
    clause_type: str
    span_text: str
    start: int
    end: int
    page: int
    line: int
    confidence: float
    match_kind: str  # pattern | keyword | trap_value


def extract_clauses(contract_text: str, pages: list[Page]) -> list[ClauseHit]:
    hits: list[ClauseHit] = []
    for ctype, patterns in CLAUSE_PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, contract_text, flags=re.IGNORECASE | re.MULTILINE):
                start, end = m.start(), m.end()
                page, line = offset_to_page_line(start, pages, contract_text)
                # Expand window for span text (120 chars each side)
                snippet = contract_text[max(0, start - 120): min(len(contract_text), end + 120)].strip()
                hits.append(ClauseHit(
                    clause_type=ctype,
                    span_text=snippet,
                    start=start, end=end,
                    page=page, line=line,
                    confidence=0.82,
                    match_kind="pattern",
                ))
        # Fuzzy keyword traps for this type
        cfg = TRAP_VALUES.get(ctype)
        if cfg and "keywords" in cfg:
            for kw in cfg["keywords"]:  # type: ignore
                for m in re.finditer(re.escape(kw), contract_text, flags=re.IGNORECASE):
                    start, end = m.start(), m.end()
                    page, line = offset_to_page_line(start, pages, contract_text)
                    snippet = contract_text[max(0, start - 120): min(len(contract_text), end + 120)].strip()
                    hits.append(ClauseHit(
                        clause_type=ctype,
                        span_text=snippet,
                        start=start, end=end,
                        page=page, line=line,
                        confidence=0.94,
                        match_kind="trap_value",
                    ))
    # Deduplicate by (type, start)
    seen: set[tuple[str, int]] = set()
    uniq: list[ClauseHit] = []
    for h in sorted(hits, key=lambda x: x.start):
        key = (h.clause_type, h.start)
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    return uniq
