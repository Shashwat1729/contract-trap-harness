import sys
sys.path.insert(0, "advanced")
from src.harness.ingest import Page
from src.core import process_contract_advanced
from src.harness.extract import extract_clauses

contract = """
SaaS Agreement
Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
Cap On Liability: Liability is capped at 12 months fees, except carve-outs for data breach are excluded from cap and not subject to limitation.
"""
pages = [Page(num=1, text=contract, start=0, end=len(contract))]
hits = extract_clauses(contract, pages)
print("hits:", [(h.clause_type, h.span_text[:60], h.confidence) for h in hits])
for h in hits:
    print(h.clause_type, h.span_text[:100])
    from src.harness.risk import assess_risk, build_evidence_package
    f = assess_risk(h)
    print("  risk:", f)
    if f:
        pkg = build_evidence_package(h, f, contract)
        print("  pkg:", pkg)
        from src.harness.verify import verify_finding
        ver = verify_finding(h.span_text, f, pkg, contract)
        print("  ver:", ver.status, ver.reasons)

res = process_contract_advanced(contract, pages, contract_id="test_01", turn=1, model="gpt-4o-mini", harness_mode="balanced")
print("result trap_count", res["trap_count"], "total", res["total_proposed"])
print("findings", res["findings"])
