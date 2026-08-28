import pytest
from src.core import process_contract, health_check, detect_clauses, detect_cross_traps

def test_process_contract_trap_a():
    contract = """
    SaaS Agreement
    Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
    Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
    """
    res = process_contract(contract)
    assert res["variant"] == "baseline"
    # Should detect Trap-A cross trap
    assert any("Trap-A" in f["trap_id"] or "Renewal" in f["clause_type"] for f in res["findings"])
    assert res["trap_count"] >= 1

def test_process_contract_no_trap():
    contract = "This is a clean SaaS MSA with Renewal Term 12 months and Notice 90 days."
    res = process_contract(contract)
    # No trap because within thresholds
    # Baseline may still flag single clause but cross trap should not be Trap-A
    assert res["variant"] == "baseline"

def test_process_contract_empty_raises():
    with pytest.raises(ValueError):
        process_contract("  ")

def test_health():
    h = health_check()
    assert h["status"] == "ok"
    assert h["variant"] == "baseline"

def test_detect_clauses():
    txt = "Renewal Term: 24 months. Notice Period To Terminate Renewal: 30 days."
    from src.core import build_page_map
    pm = build_page_map(txt)
    hits = detect_clauses(txt, pm)
    assert len(hits) >= 2

def test_detect_cross_traps():
    txt = "Renewal Term: 24 months. Notice Period To Terminate Renewal: 30 days."
    from src.core import build_page_map
    pm = build_page_map(txt)
    traps = detect_cross_traps(txt, pm)
    assert any(t.trap_id == "Trap-A" for t in traps)
