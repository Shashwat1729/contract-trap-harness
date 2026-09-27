from src.harness.ingest import Page
from src.core import process_contract_advanced
from src.harness.verify import verify_finding
from src.harness.extract import extract_clauses
from src.harness.risk import assess_risk, build_evidence_package

def test_advanced_trap_gated():
    contract = """
    SaaS Agreement
    Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
    Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
    Cap On Liability: Liability is capped at 12 months fees, except carve-outs for data breach are excluded from cap and not subject to limitation.
    """
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    res = process_contract_advanced(contract, pages, contract_id="test_01", turn=1, model="gpt-4o-mini", harness_mode="balanced")
    assert res["variant"] == "advanced"
    assert res["trap_count"] >= 2  # Trap-A and Trap-B should be approved
    # All approved should be PASS
    for f in res["findings"]:
        if f["verification"] == "PASS":
            assert f["evidence"]["contract_page"] >= 1
            assert f["surgical"] is True or len(f["proposed_change"]) < 500
    assert res["evidence_supported"] == res["trap_count"]
    assert res["surgical_rate"] > 0.5

def test_advanced_no_trap_stays_clean():
    contract = "Clean SaaS MSA: Renewal Term 12 months, Notice 90 days, Liability capped at 12 months fees."
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    res = process_contract_advanced(contract, pages, contract_id="clean", turn=1)
    # No trap because within thresholds, so 0 approved
    assert res["trap_count"] == 0

def test_advanced_empty_raises():
    import pytest
    pages = [Page(num=1, text="", start=0, end=0)]
    with pytest.raises(ValueError):
        process_contract_advanced("  ", pages, contract_id="x")

def test_extract_clauses():
    contract = "Renewal Term: 24 months. Notice Period To Terminate Renewal: 30 days. Cap On Liability: uncapped."
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    hits = extract_clauses(contract, pages)
    types = {h.clause_type for h in hits}
    assert "Renewal Term" in types
    # case-insensitive check for notice type
    assert any(t.lower() == "notice period to terminate renewal".lower() for t in types)

def test_verify_gates():
    contract = "Renewal Term: 24 months"
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    hits = extract_clauses(contract, pages)
    hit = [h for h in hits if h.clause_type == "Renewal Term"][0]
    finding = assess_risk(hit)
    assert finding is not None
    pkg = build_evidence_package(hit, finding, contract)
    ver = verify_finding(hit.span_text, finding, pkg, contract)
    assert ver.status == "PASS"

def test_llm_verify_confidence_routing_skips_high_confidence_only(monkeypatch):
    """
    CHANGELOG #20: the LLM cross-check should be skipped only for findings the dual
    verifier agreed PASS on AND whose playbook confidence is already high (>=
    LLM_VERIFY_SKIP_CONFIDENCE, default 0.85) -- routed (real call attempted) for
    lower-confidence findings even when dual-agree-pass. This fixture's own findings
    span both sides of that line for real (not contrived): Renewal Term (0.88) and
    Cap-on-Liability (carve-out-bypass, 0.91) skip; Notice Period (0.84) routes to a
    real call. (The Renewal clause matches two regex patterns -- "Renewal Term" and
    "automatically renew" -- which extract.py now collapses into ONE hit; it used to
    surface as two identical findings.)
    """
    import src.core as core_mod

    monkeypatch.setattr(core_mod, "ENABLE_LLM_VERIFY", True)
    calls = {"n": 0}

    def _fake_llm_verify_finding(*args, **kwargs):
        calls["n"] += 1
        from src.harness.llm_verify import LLMVerifyResult
        return LLMVerifyResult(ran=True, supported=True, confidence=0.9, concern="", mock=True)

    monkeypatch.setattr(core_mod, "llm_verify_finding", _fake_llm_verify_finding)

    contract = """
    SaaS Agreement
    Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
    Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
    Cap On Liability: Liability is capped at 12 months fees, except carve-outs for data breach are excluded from cap and not subject to limitation.
    """
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    res = process_contract_advanced(contract, pages, contract_id="routing_test", turn=1)

    assert res["dual_stats"]["agree_pass"] == 3  # all 3 findings pass the deterministic gate
    assert res["llm_stats"]["skipped_high_confidence"] == 2  # Renewal (0.88) + Cap-on-Liability (0.91)
    assert calls["n"] == 1  # only Notice Period (0.84) actually reaches the real call
    assert res["llm_stats"]["ran"] == 1


def test_verify_rejects_hallucinated():
    from src.harness.verify import verify_finding
    from src.harness.risk import RiskFinding
    contract = "Clean contract no trap"
    finding = RiskFinding(clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="PR-01", proposed_change="Change", rationale="test", confidence=0.9, evidence_contract_span="hallucinated span not in contract", evidence_page=99, evidence_line=99)
    pkg = {"contract_span": "hallucinated span not in contract", "contract_page": 99, "playbook_rule": "P-01", "precedent": {"id":"PR-01"}, "confidence": 0.9}
    ver = verify_finding("hallucinated span not in contract", finding, pkg, contract)
    assert ver.status == "REJECT"


def test_llm_extract_generates_candidate_that_becomes_a_real_approved_finding(monkeypatch):
    """
    CHANGELOG #22 (strengthened after a strict-audit finding: the original version of
    this test used Termination for Convenience, whose only playbook rule triggers on
    ABSENCE not presence, so assess_risk necessarily returned None and the test never
    actually proved a generated candidate could become a real finding -- it only proved
    the hit didn't crash). This version uses Cap on Liability with a real "uncapped"
    trap keyword, which DOES trigger P-04 in assess_risk -- so this test proves the
    full, novel claim: an LLM-generated candidate flows through assess_risk (real
    trap logic fires), dual_verify_finding (real span-in-contract check passes,
    because the span genuinely is a substring of contract_text), and comes out the
    other end as a real approved (PASS) finding, exactly like a regex hit would.
    llm_extract_missing_clauses itself is mocked here (its own anti-hallucination
    substring logic is covered by test_llm_extract.py); this test verifies core.py's
    WIRING end to end through the real downstream pipeline.
    """
    import src.core as core_mod
    from src.harness.extract import ClauseHit

    monkeypatch.setattr(core_mod, "ENABLE_LLM_EXTRACT", True)

    # Deliberately avoids the literal phrase "cap on liability" / "liability cap" (extract.py's
    # own regex pattern for this clause type -- see extract.py's CLAUSE_PATTERNS) so the
    # real regex layer does NOT also independently tag this sentence -- keeping this a clean
    # test of the generated candidate alone, not a coincidental double-match.
    contract = (
        "SaaS Agreement\n"
        "Renewal Term: This Agreement shall automatically renew for successive 24 month periods.\n"
        "Section 9. Liability arising under this Agreement shall be uncapped for any claim.\n"
    )
    cap_span = "Liability arising under this Agreement shall be uncapped for any claim."
    start = contract.index(cap_span)

    def _fake_generate(contract_text, pages, existing_hits, max_calls=6):
        # llm_extract_missing_clauses itself is fully mocked here -- this test verifies
        # core.py's WIRING (merge into clause_hits -> real assess_risk/dual_verify), not
        # the real function's own "only generate for missing types" filtering logic
        # (covered separately in test_llm_extract.py).
        return [ClauseHit(
            clause_type="Cap on Liability", span_text=cap_span,
            start=start, end=start + len(cap_span), page=1, line=1,
            confidence=0.55, match_kind="llm_generated",
        )]

    monkeypatch.setattr("src.harness.llm_extract.llm_extract_missing_clauses", _fake_generate)

    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    res = process_contract_advanced(contract, pages, contract_id="llm_extract_test", turn=1)

    assert res["llm_extract_generated"] == 1
    cap_findings = [f for f in res["findings"] if f["clause_type"] == "Cap on Liability"]
    assert len(cap_findings) == 1  # assess_risk's "uncapped" trap genuinely fired for the generated hit
    assert cap_findings[0]["rule_id"] == "P-04"
    assert cap_findings[0]["verification"] == "PASS"  # dual_verify's real span-in-contract check passed
    assert cap_findings[0] in res["approved_candidates"]


def test_llm_extract_disabled_by_default_leaves_clause_hits_unchanged(monkeypatch):
    import src.core as core_mod
    called = {"n": 0}

    def _should_not_be_called(*a, **kw):
        called["n"] += 1
        return []

    monkeypatch.setattr("src.harness.llm_extract.llm_extract_missing_clauses", _should_not_be_called)
    contract = "SaaS Agreement\nRenewal Term: This Agreement shall automatically renew for successive 24 month periods.\n"
    pages = [Page(num=1, text=contract, start=0, end=len(contract))]
    res = process_contract_advanced(contract, pages, contract_id="llm_extract_off_test", turn=1)
    assert called["n"] == 0
    assert res["llm_extract_generated"] == 0
