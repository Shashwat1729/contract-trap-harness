import re
contract = """
SaaS Agreement
Renewal Term: This Agreement shall automatically renew for successive 24 month periods.
Notice Period To Terminate Renewal: Notice must be provided at least 30 days prior to renewal.
"""
# Simulate hit
from pathlib import Path
import sys
sys.path.insert(0, "advanced")
from src.harness.extract import extract_clauses
from src.harness.ingest import Page
pages = [Page(num=1, text=contract, start=0, end=len(contract))]
hits = extract_clauses(contract, pages)
for h in hits:
    print(repr(h.clause_type), repr(h.span_text[:120]))
    # Check renewal logic
    if h.clause_type == "Renewal Term":
        m = re.search(r"(\d+)\s*months?", h.span_text, flags=re.IGNORECASE)
        print("  renewal m:", m.group(1) if m else None)
        if m:
            print("  val", int(m.group(1)) > 12)
        # Also test our new pattern
        m2 = re.search(r"renewal term[\s\S]{0,150}?(\d+)\s*months?", h.span_text, flags=re.IGNORECASE)
        print("  renewal pattern2:", m2.group(1) if m2 else None)
