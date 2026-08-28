import json, re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from baseline.src.core import process_contract as bl
from advanced.src.harness.ingest import Page
from advanced.src.core import process_contract_advanced

FIXTURES = Path("shared/fixtures/contracts")
# Pick one injected trap-A contract: look for cuad_00 which should be injected
for cid in ["cuad_00","cuad_01","cuad_02"]:
    txt = (FIXTURES / f"{cid}.txt").read_text(encoding="utf-8")
    meta = json.loads((FIXTURES / f"{cid}.json").read_text(encoding="utf-8"))
    print(f"\n=== {cid} ===")
    print("Gold traps:", [(t["id"], t["exists"]) for t in meta["trap_gold"]])
    # Check if injected text present
    print("Has ADDENDUM:", "ADDENDUM TRAP-A" in txt)
    print("Has 24 month:", "24 month" in txt)
    print("Has 30 days:", "30 days" in txt)
    # Baseline
    b = bl(txt)
    print("Baseline findings:", [(f["trap_id"], f["clause_type"]) for f in b["findings"][:5]])
    print("Baseline trap_count", b["trap_count"])
    # Advanced
    pages = []
    cpt=2500
    for i in range(0, len(txt), cpt):
        pages.append(Page(num=i//cpt+1, text=txt[i:i+cpt], start=i, end=i+len(txt[i:i+cpt])))
    if not pages:
        pages.append(Page(num=1, text=txt, start=0, end=len(txt)))
    a = process_contract_advanced(txt, pages, contract_id=cid, turn=1, model="gpt-4o-mini", harness_mode="balanced")
    print("Advanced findings:", [(f["trap_id"], f["clause_type"], f["verification"]) for f in a["findings"][:5]])
    print("Advanced trap_count", a["trap_count"], "total", a["total_proposed"])
    print("Advanced trap_interactions", a["trap_interactions"])
    # Check trap recall logic
    gold = [g for g in meta["trap_gold"] if g["exists"]]
    for g in gold:
        b_hit = any(f["trap_id"] == g["id"] or g["id"] in f.get("trap_id","") for f in b["findings"])
        a_hit = any(f["trap_id"] == g["id"] or g["id"] == f.get("rule_id","") or g["id"] in f.get("trap_id","") for f in a["findings"])
        print(f"Gold {g['id']} exists, b_hit {b_hit}, a_hit {a_hit}")
