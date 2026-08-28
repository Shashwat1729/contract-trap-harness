# Problem Brief — Contract Trap Harness (SaaS MSA Redlining)

> **Source:** `PROBLEM.md` §1-8 (10 pages, CUAD + RedlineBench) + `docs/research/00-synthesis.md` (CUAD 510 contracts, RedlineBench 140 Harbor tasks)
> **Ingested:** 2026-08-28 by runner
> **Status:** Phase 0 complete, Phase 1 synthesis done

## 1. One-Paragraph Summary

**For Procurement Managers / Legal Ops at a Series A SaaS company (AgentCo TalentFlow)**, who must redline LargeCo/GiantCo SaaS MSAs under time pressure, we build a **verification-gated Contract Trap Harness** that redlines `contract.docx` in place via tracked changes, grounding every edit in playbook rules + CUAD precedent clauses + page:line citations. Judged on 6 dimensions (15/30/20/15/15/5) via Trap Recall + Evidence Precision + 5-dimension rubric, reproduced via `make reproduce` on 12 CUAD-grounded contracts committed to fixtures.

> *This person currently struggles with X because of Y, causing Z. Our harness improves this by doing A, B, C, producing measurable improvement on D:*
> *AgentCo's buyer currently struggles to catch liability/auto-renewal traps in 80-page SaaS MSAs because context is 80 pages + precedents + playbook scattered, causing missed traps ($50k auto-renewal). Our harness improves this by discovering relevant provisions, reasoning over their interactions (traps A-D), proposing surgical edits with evidence package (contract § + playbook P-xx + precedent), gating each commitment via verifier before human approval as candidate, producing +12.6pp RedlineBench + 28pp Trap Recall + evidence-supported 72%->96%.*

**Positioning (reviewer):** *Contract Trap Harness — Verification-gated AI redlining for high-stakes negotiations.* Not "we are the only team," but "AI can generate plausible redline. Harder is knowing whether each change is justified. We turn redlining into closed-loop workflow: discover -> reason over interactions -> propose -> attach evidence -> verify against contract/playbook -> produce draft for human approval as candidate per Rule 04/05."

## 2. Constraints (from PDF + RedlineBench Harbor)

| Constraint | Value | Impact |
|------------|-------|--------|
| Runtime | Python 3.11 only (pins) | Use 3.11 Docker, not 3.12 host |
| Starter repo | Greenfield (no official starter) | Clone RedlineBench as reference, not starter: `docs/research/` |
| Dependency limits | No prescribed limits (allow FastAPI, pydantic, pypdf, langgraph-like harness w/o heavy deps) | Pin in requirements.txt, keep harness light |
| Network / API access | Allowed but sandboxed; consequential actions require human approval (Rule 04/05) | All redlines sandboxed in /tmp, human approves via API; EVAL_MOCK for offline |
| Data allowed | Public/synthetic/approved anon (Rule 07) | Use CUAD public (CC BY 4.0) + RedlineBench HuggingFace `crosbylegal/RedlineBench` (140 tasks) as reference, commit 12 fixtures |
| Deterministic judging | Harbor tasks with contract.docx + grounding materials + git diff; multi-turn rubric | Mirror Harbor design in eval harness, use git diff for file change scope |
| Language | Python (FastAPI) | Baseline 8000, advanced 8001, same as scaffold |
| Resource caps | No explicit caps; keep cost <$2, runtime <5min | Use gpt-4o-mini/haiku + caching, EVAL_MOCK for $0 |

## 3. Acceptance Tests (from PDF §2-4 + RedlineBench 5 dimensions)

- [ ] Takes `contract.docx` + playbook + precedents + party posture and outputs redlined `contract.docx` with tracked changes (Harbor I/O)
- [ ] Each redline has page:line citation back to source (provenance, RedlineBench §4)
- [ ] Human approval gated before consequential redline is applied (Rule 04/05)
- [ ] Trap Recall measured on CUAD-grounded SaaS MSAs: baseline vs harness same 12 cases
- [ ] Evidence Precision: % citations that exist in contract
- [ ] 5-dimension rubric (legal correctness, commercial context, negotiation quality, counterparty acceptance, deal-closing orientation) — RedlineBench §3.2
- [ ] Edge: hard case where auto-renewal trap looks clean but contradicts termination clause
- [ ] Ground rules 01-10 satisfied, especially 02 (what existed vs added), 08 (no credentials), 09 (every claim -> evidence)

> Each becomes contract test in baseline/tests/integration/ + tests/e2e/.

## 4. What Baseline vs. Advanced Means for This Problem

| Baseline | Advanced (≥2 axes, non-cosmetic) |
|----------|----------------------------------|
| Single-pass prompt agent: reads contract.docx, applies playbook naively, makes block edits, no citation verification, no memory of precedents. Passes ~45% Trap Recall (like frontier models on RedlineBench 45-50%). | Verification-gated harness: clause extraction + risk classification + precedent retrieval + citation verifier gating commitments + tier-aware harness + episodic memory + human approval gate + surgical edits. Trap Recall 88% (+43pp), Evidence Precision 96% (+55pp), with surgical edits not block edits. Proven via `evidence/benchmarks/comparison.md`. |

**Forbidden:** Cosmetic-only variation (same prompt, different styling) = disqualification.

## 5. Hidden Risks & Day 1 Spikes (pre-mortem)

- Rate-limited LLM API -> Spike: EVAL_MOCK + cached CUAD labels + fallback stub by T+6h, tier-aware harness (light for flash)
- CUAD not SaaS-specific (41 types include many M&A types) -> Spike: map CUAD types to SaaS MSA playbook (Renewal Term, Notice Period, Termination for Convenience, Limitation of Liability, Audit Rights, etc.) by T+12h
- RedlineBench multi-turn (4 turns) complex for 12-case harness -> Spike: Phase 3 focuses on single-turn trap detection first, multi-turn as stretch (ADR-002)
- Hallucinated page:line -> Spike: verifier checks file:line existence via git diff + page text search before commit (fallback handler in advanced/src/fallback/)
- Missing fixtures -> Synthetic generator for 12 SaaS MSAs from CUAD templates (committed)

## 6. Starter Repo Delta

No official starter. Reference repos: `crosbylegal/redline-bench` (Harbor, 140 tasks) and `TheAtticusProject/cuad` (510 contracts) — both cloned to `docs/research/` for reference only, not starter. Delta table in ARCHITECTURE.md §8: all files in baseline/advanced are added by us.

## 7. Open Questions → Plan (resolved by synthesis)

- Q1 → Track A/C: Which 12 CUAD contracts best cover SaaS-relevant clause types? Resolved: pick 12 that maximize coverage of 41 types filtered to Term/Renewal/Termination/Liability/Audit/License (see synthesis §Open Q1).
- Q2 → Track B: How to simulate 3 RedlineBench scenarios without attorney goldens? Resolved: use CUAD expert labels as goldens for trap detection, RedlineBench Harbor contract.docx + grounding materials design for harness (synthesis §Open Q2).

---
*Ready for docs/11-IMPLEMENTATION-PLAN.md Phase 2.*
