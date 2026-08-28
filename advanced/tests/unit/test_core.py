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

def test_verify_rejects_hallucinated():
    from src.harness.verify import verify_finding
    from src.harness.risk import RiskFinding
    contract = "Clean contract no trap"
    finding = RiskFinding(clause_type="Renewal Term", risk="High", rule_id="P-01", precedent_id="PR-01", proposed_change="Change", rationale="test", confidence=0.9, evidence_contract_span="hallucinated span not in contract", evidence_page=99, evidence_line=99)
    pkg = {"contract_span": "hallucinated span not in contract", "contract_page": 99, "playbook_rule": "P-01", "precedent": {"id":"PR-01"}, "confidence": 0.9}
    ver = verify_finding("hallucinated span not in contract", finding, pkg, contract)
    assert ver.status == "REJECT"
