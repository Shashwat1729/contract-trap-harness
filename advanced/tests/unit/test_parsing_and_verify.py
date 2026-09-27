"""
Regression tests for duration parsing, same-clause hit de-duplication, and the
verifier's span-provenance check.
"""
from __future__ import annotations

import pytest

from src.core import _trap_interactions, process_contract_advanced
from src.harness.extract import extract_clauses, find_durations, parse_days, parse_months
from src.harness.ingest import Page
from src.harness.risk import (
    INITIAL_TERM_LEAD_IN,
    RENEWAL_KEYWORD,
    RiskFinding,
    _find_number_before_unit,
    _find_number_near_keyword,
)
from src.harness.verify import dual_verify_finding, verify_finding


def _pages(text: str) -> list[Page]:
    return [Page(num=1, text=text, start=0, end=len(text))]


@pytest.mark.parametrize("text,expected", [
    ("renews for thirty-six months", 36),          # used to parse as 6 ("six" inside "thirty-six")
    ("twenty-four (24) months", 24),
    ("twenty four months", 24),
    ("thirty-six (36) calendar months", 36),
    ("36 months", 36),
    ("two (2) years", 24),                          # years were not recognised at all
    ("successive one (1) year terms", 12),
    ("a one-year term", 12),
    ("12 monthly installments", None),              # "monthly" is not a duration
    ("on a month-to-month basis", 1),               # "a month" -- a 1-month rolling renewal
    ("month-to-month", None),
    ("no duration here", None),
])
def test_parse_months(text, expected):
    assert parse_months(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("upon written notice of ninety days", 90),     # used to parse as 10 ("ten" inside "written")
    ("thirty (30) days", 30),
    ("ten business days", 10),
    ("Sixty-Day notice", 60),
    ("1,000 days", None),
    ("within days", None),
])
def test_parse_days(text, expected):
    assert parse_days(text) == expected


def test_find_durations_reports_offsets_in_order():
    text = "Initial term of twelve (12) months; renewal term of three (3) years."
    assert [v for _, v in find_durations(text, "month")] == [12, 36]
    assert find_durations(text, "month", include_years=False) == [(text.index("twelve"), 12)]


def test_risk_number_helpers_accept_spelled_out_numbers():
    assert _find_number_before_unit("Notice of ninety days is required.", "days?") == 90
    assert _find_number_before_unit("renews for two (2) years", "months?") == 24


def test_renewal_lookup_skips_initial_term_after_header_keyword():
    span = (
        "9. Term and Renewal\n\nThis Agreement continues for an initial period of one year "
        "(the \"Initial Term\"). Thereafter it renews for successive terms of thirty-six (36) months."
    )
    assert _find_number_near_keyword(span, RENEWAL_KEYWORD, "months?") == 12  # naive: header window
    assert _find_number_near_keyword(span, RENEWAL_KEYWORD, "months?", skip_if_preceded_by=INITIAL_TERM_LEAD_IN) == 36


def test_one_clause_matched_by_two_patterns_is_one_hit():
    text = "Renewal Term: This Agreement shall automatically renew for successive 24 month periods."
    hits = [h for h in extract_clauses(text, _pages(text)) if h.clause_type == "Renewal Term"]
    assert len(hits) == 1


def test_distinct_same_type_clauses_are_kept():
    filler = "Other boilerplate text. " * 40
    text = (
        "Section 1. Renewal Term: renews for 24 months.\n" + filler
        + "\nSection 9. Renewal Term: the reseller addendum renews for 36 months.\n"
    )
    hits = [h for h in extract_clauses(text, _pages(text)) if h.clause_type == "Renewal Term"]
    assert len(hits) == 2


def test_trap_a_is_reported_once_per_clause_pair():
    text = (
        "Renewal Term: This Agreement shall automatically renew for successive 24 month periods.\n"
        "Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.\n"
    )
    pages = _pages(text)
    traps = _trap_interactions(text, extract_clauses(text, pages), pages)
    assert [t["id"] for t in traps].count("Trap-A") == 1


def test_spelled_out_renewal_trap_is_detected_end_to_end():
    text = (
        "Section 8 -- Renewal Term. Upon expiry this Agreement automatically renews for "
        "successive periods of two (2) years.\n"
        "Section 9 -- Notice of Non-Renewal. Either party may give notice of non-renewal "
        "no later than thirty days before the end of the then-current term.\n"
    )
    res = process_contract_advanced(text, _pages(text), contract_id="words_test")
    approved = {f["rule_id"] for f in res["approved_candidates"]}
    assert {"P-01", "P-02"} <= approved
    assert any(t["id"] == "Trap-A" for t in res["trap_interactions"])


def _finding(span: str) -> tuple[RiskFinding, dict]:
    f = RiskFinding(
        clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="Acme",
        proposed_change="Initial Term 12 months, renewal Term 12 months.", rationale="r",
        confidence=0.88, evidence_contract_span=span, evidence_page=4, evidence_line=1,
    )
    pkg = {"contract_span": span, "contract_page": 4, "playbook_rule": "P-01",
           "precedent": {"id": "PR-01"}, "confidence": 0.88}
    return f, pkg


def test_verbatim_span_deep_in_document_with_irregular_whitespace_passes():
    # The span sits well past char 8000 and contains a line break + double space: a
    # genuine citation that the old 8000-char normalized window reported as hallucinated.
    clause = "Renewal Term.  This Agreement shall\nautomatically renew for successive twenty-four (24) month periods."
    text = ("Lorem ipsum dolor sit amet. " * 400) + clause + " Tail text."
    assert text.index(clause) > 8000
    f, pkg = _finding(clause)
    assert verify_finding(clause, f, pkg, text).status == "PASS"
    ver = dual_verify_finding(clause, f, pkg, text)
    assert ver.status == "PASS" and ver.dual_mode == "dual-agree-pass"


def test_fabricated_span_is_rejected_by_both_thresholds():
    text = ("Lorem ipsum dolor sit amet. " * 400) + "Renewal Term: 12 months."
    span = "Vendor may renew this agreement for ninety-nine years at its sole discretion."
    f, pkg = _finding(span)
    ver = dual_verify_finding(span, f, pkg, text)
    assert ver.status == "REJECT" and ver.dual_mode == "dual-agree-reject"


def test_span_whose_tail_is_altered_is_borderline_not_pass():
    base = "Renewal Term. This Agreement shall automatically renew for successive twenty-four (24) month periods unless terminated."
    text = ("Lorem ipsum dolor sit amet. " * 50) + base
    altered = base.replace("unless terminated", "and the Customer waives every right to object, forever and irrevocably")
    f, pkg = _finding(altered)
    assert dual_verify_finding(altered, f, pkg, text).status == "REJECT"


def test_liability_clause_matching_both_cap_types_yields_one_finding_and_one_trap():
    text = (
        "Section 9. Limitation of Liability. The liability cap is 12 months of fees; provided that "
        "the foregoing cap shall not apply to data breach, which is excluded from cap."
    )
    res = process_contract_advanced(text, _pages(text), contract_id="cap_dupe")
    assert [f["rule_id"] for f in res["findings"]] == ["P-12"]
    traps = [t for t in res["trap_interactions"] if t["id"] == "Trap-B"]
    assert len(traps) == 1
    assert set(traps[0]["related"]) == {"Cap on Liability", "Limitation of Liability"}
