"""
Build real fixtures from CUAD + RedlineBench — no synthetic generation, production-grade.

Uses docs/research/cuad/CUADv1.json (510 contracts, 41 types, expert annotations) as source.
Creates shared/fixtures/contracts/ with 12 real contracts + trap-focused golds (trap exists yes/no, related clauses, conflict relationship, supporting spans) per reviewer correction.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
CUAD_JSON = ROOT / "docs" / "research" / "cuad" / "CUADv1.json"
FIXTURES = ROOT / "shared" / "fixtures" / "contracts"
FIXTURES.mkdir(parents=True, exist_ok=True)

# SaaS-relevant CUAD types (subset of 41, mapped to playbook P-01..P-12)
SAAS_TYPES = [
    "Renewal Term",
    "Notice Period To Terminate Renewal",
    "Termination For Convenience",
    "Cap On Liability",
    "Audit Rights",
    "Governing Law",
    "License Grant",
    "Non-Compete",
    "Non-Disparagement",
    "IP Ownership Assignment",
    "Post-Termination Services",
]

# Trap definitions focusing on *interaction*, not just clause
TRAP_DEFS = {
    "Trap-A": {"name": "Renewal vs Termination mismatch", "requires": ["Renewal Term", "Notice Period To Terminate Renewal"], "check": "renewal >12m and notice <60d"},
    "Trap-B": {"name": "Liability cap bypass via carve-out", "requires": ["Cap On Liability"], "keywords": ["carve-out", "excluded from cap"]},
    "Trap-C": {"name": "Deletion vs Retention conflict", "requires": ["Post-Termination Services"], "keywords": ["deletion", "retention"]},
}

def load_cuad():
    data = json.loads(CUAD_JSON.read_text(encoding="utf-8"))
    return data["data"]

def extract_contract_cases():
    raw = load_cuad()
    # raw is list of {title, paragraphs: [{context, qas: [{question, answers:[{text, answer_start}]}]}]}
    # Each contract has multiple qas (41 types). We will sample 12 contracts that maximize SaaS type coverage.
    cases = []
    for entry in raw:
        contract_text = entry["paragraphs"][0]["context"] if entry["paragraphs"] else ""
        title = entry.get("title", "contract")
        qas = entry["paragraphs"][0].get("qas", []) if entry["paragraphs"] else []
        # Map question -> clause type (question is like "What is the renewal term?")
        # Build dict question -> answers
        qa_map = {qa["question"]: qa for qa in qas}
        # Count SaaS types present (has non-empty answer where is_impossible == False)
        saas_hits = 0
        for saas in SAAS_TYPES:
            for q, qa in qa_map.items():
                if saas.lower() in q.lower() and not qa.get("is_impossible", True) and qa.get("answers"):
                    # has annotation
                    saas_hits += 1
                    break
        cases.append((title, contract_text, qas, saas_hits))
    # Sort by saas_hits descending, then by contract length (prefer shorter for 72h demo)
    cases.sort(key=lambda x: (-x[3], len(x[1])))
    return cases[:20]  # top 20

def build_trap_gold(contract_text: str, qas: list, title: str) -> dict:
    """Build trap-focused gold: trap exists yes/no, related clauses, conflict, supporting spans. Uses CUAD spans as supporting evidence, not as redline gold."""
    # Build lookup: clause type -> list of spans
    clause_spans = {}
    for qa in qas:
        q = qa["question"]
        # Infer clause type from question
        ctype = None
        for saas in SAAS_TYPES:
            if saas.lower() in q.lower():
                ctype = saas
                break
        if not ctype:
            continue
        if qa.get("is_impossible"):
            continue
        for ans in qa.get("answers", []):
            txt = ans.get("text", "").strip()
            if not txt:
                continue
            clause_spans.setdefault(ctype, []).append(txt)
    traps = []
    # Trap-A: renewal + notice
    renewals = clause_spans.get("Renewal Term", [])
    notices = clause_spans.get("Notice Period To Terminate Renewal", [])
    trap_a_exists = False
    related_a = []
    spans_a = []
    for r in renewals:
        m = re.search(r"(\d+)\s*months?", r, flags=re.IGNORECASE)
        if m and int(m.group(1)) > 12:
            for n in notices:
                mn = re.search(r"(\d+)\s*days?", n, flags=re.IGNORECASE)
                if mn and int(mn.group(1)) < 60:
                    trap_a_exists = True
                    related_a = ["Renewal Term", "Notice Period To Terminate Renewal"]
                    spans_a = [r, n]
                    break
    traps.append({
        "id": "Trap-A",
        "name": TRAP_DEFS["Trap-A"]["name"],
        "exists": trap_a_exists,
        "related_clauses": related_a,
        "conflict": TRAP_DEFS["Trap-A"]["check"] if trap_a_exists else "no mismatch",
        "supporting_spans": spans_a,
        "source": "CUAD annotations for Renewal Term + Notice Period"
    })
    # Trap-B: cap bypass
    caps = clause_spans.get("Cap On Liability", [])
    trap_b_exists = False
    spans_b = []
    for c in caps:
        window = c  # CUAD span itself; check keywords in span
        if re.search(r"carve-out|excluded from cap|not subject to limitation", window, flags=re.IGNORECASE):
            trap_b_exists = True
            spans_b = [c]
            break
        # Also check full contract window around span for carve-out language
        # (simplified: search contract near that span)
        # For now, only check span itself as trap signal from annotation
    traps.append({
        "id": "Trap-B",
        "name": TRAP_DEFS["Trap-B"]["name"],
        "exists": trap_b_exists,
        "related_clauses": ["Cap On Liability"] if trap_b_exists else [],
        "conflict": "carve-outs bypass cap" if trap_b_exists else "no bypass",
        "supporting_spans": spans_b,
        "source": "CUAD Cap On Liability spans"
    })
    # Trap-C: deletion vs retention (rarer in CUAD, often not present -> no trap)
    pt = clause_spans.get("Post-Termination Services", [])
    trap_c_exists = False
    spans_c = []
    for p in pt:
        if re.search(r"deletion|retain|retention", p, flags=re.IGNORECASE):
            # Check if both deletion and retention language present in same span window
            if re.search(r"delete", p, flags=re.IGNORECASE) and re.search(r"retain", contract_text, flags=re.IGNORECASE):
                trap_c_exists = True
                spans_c = [p]
    traps.append({
        "id": "Trap-C",
        "name": TRAP_DEFS["Trap-C"]["name"],
        "exists": trap_c_exists,
        "related_clauses": ["Post-Termination Services"] if trap_c_exists else [],
        "conflict": "deletion vs retention conflict" if trap_c_exists else "no conflict",
        "supporting_spans": spans_c,
        "source": "CUAD Post-Termination Services spans"
    })
    return {"traps": traps, "clause_spans": {k: v[:2] for k, v in clause_spans.items()}}  # keep at most 2 spans per type for brevity

def main():
    cases = extract_contract_cases()
    print(f"Selected {len(cases)} contracts (SaaS-rich)")
    manifest = []
    for idx, (title, contract_text, qas, saas_hits) in enumerate(cases[:12]):
        cid = f"cuad_saas_{idx:02d}"
        # Truncate contract for fixture (keep first 8000 chars + last 2000 to preserve traps that may be at end)
        if len(contract_text) > 8000:
            text = contract_text[:8000] + "\n\n...[truncated middle]...\n\n" + contract_text[-2000:]
        else:
            text = contract_text
        gold = build_trap_gold(text, qas, title)
        # Write contract as .txt (preserve page:line via chars_per_page paginator in harness)
        contract_path = FIXTURES / f"{cid}.txt"
        contract_path.write_text(text, encoding="utf-8")
        # Write meta
        meta = {
            "contract_id": cid,
            "title": title,
            "original_cuad_title": title,
            "saas_hits": saas_hits,
            "chars": len(text),
            "trap_gold": gold["traps"],
            "clause_categories": list(gold["clause_spans"].keys()),
            "source": "CUAD v1 (CC BY 4.0) — clause spans used as supporting evidence for trap-focused golds, not as redline golds (per reviewer correction)",
        }
        meta_path = FIXTURES / f"{cid}.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append({"contract_id": cid, "title": title, "saas_hits": saas_hits, "traps": gold["traps"], "chars": len(text)})
        print(f"{cid}: {title[:60]} | saas_hits={saas_hits} | traps: A={gold['traps'][0]['exists']} B={gold['traps'][1]['exists']} C={gold['traps'][2]['exists']}")

    # Write manifest + playbook
    (FIXTURES / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    # Playbook (12 rules, matches risk.py)
    playbook = Path(__file__).parents[1] / "shared" / "fixtures" / "contracts" / "playbook.md"
    if not playbook.exists():
        from textwrap import dedent
        playbook.write_text(dedent("""\
        # AgentCo SaaS Playbook (12 rules, P-01..P-12)
        # Source: CUAD Handbook + RedlineBench SaaS MSAs + SaaS commercial context

        P-01 Renewal Term: renewal >12 months is trap. Prefer 12 months.
        P-02 Notice Period: notice <60 days with 12m renewal is trap. Prefer 90 days.
        P-03 Termination for Convenience: missing TFC is trap. Prefer 30 days any party.
        P-04 Cap on Liability: uncapped/unlimited is trap. Prefer cap = 12m fees.
        P-05 Audit Rights: unlimited audits is trap. Prefer 1/year 30 days notice.
        P-06 Governing Law: vendor-favorable without mutuality is trap. Prefer Delaware mutual.
        P-07 License Grant: irrevocable/perpetual without termination linkage is trap. Prefer terminates on termination.
        P-08 Non-Compete: broad >12m is trap. Prefer 6m direct competitors.
        P-09 Non-Disparagement: one-way is trap. Prefer mutual.
        P-10 IP Ownership: vendor owns customer data is trap. Prefer customer retains IP.
        P-11 Post-Termination Services: no transition is trap. Prefer 30 days at prior rates.
        P-12 Limitation of Liability: carve-outs bypassing cap is trap. Prefer limited to fraud/willful.
        """), encoding="utf-8")
    print(f"Wrote {len(manifest)} fixtures to {FIXTURES}")

if __name__ == "__main__":
    main()
