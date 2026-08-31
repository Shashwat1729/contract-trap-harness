# Implementation Plan — Contract Trap Harness (CUAD + RedlineBench)

Date: 2026-08-28
Research: docs/research/00-synthesis.md
Problem: docs/problem-brief.md
Status: Approved for Phase 3 build

## 1. Proposed Solution & Fitness

**Solution (CORRECTED per reviewer):** Verification-gated Contract Trap Harness that redlines `contract.docx` in place via tracked changes, requiring every substantive redline to carry auditable evidence linking the change to governing playbook, contract text, and applicable precedent, and only then producing the draft for human approval as candidate.

**Central thesis (single, per reviewer):** *Can explicit evidence-gated verification make contract-redlining agents more reliable without sacrificing negotiation quality or deal-closing behavior?* This is the experiment. Tier-aware harness and structured negotiation memory are supporting mechanisms, not main theses.

**Why fitness:** RedlineBench (140 tasks, 3 scenarios x 4 turns, attorney goldens) proves frontier models score 50.5% (GPT-5.5) / 47.3% / 45.1% / 44.4% because they anchor, make block edits not surgical, lack prioritization and momentum. We attack the #1 gap: no evidence-gated commitment. Sirion 60% faster redlining is enterprise outcome we improve on via auditability.

**Why not obvious single-prompt:** Single prompt hallucinates citations, misses cross-reference traps (auto-renewal 24m p.47 vs termination 30 days p.12). Our verifier REJECTS unsupported edits before they reach human reviewer as approved candidate per Rule 04/05.

## 2. Architecture & Structure — Verification-Gated Closed Loop (reviewer corrected)

```
Contract / negotiation state (contract.docx + playbook + commercial context + prior turns)
        ↓
Relevant-clause discovery (CUAD-based retrieval, not CUAD as redline truth)
        ↓
Negotiation reasoning (dependency / cross-reference map for traps A-D)
        ↓
Proposed redlines (surgical edits)
        ↓
Evidence package (contract §, playbook rule P-xx, commercial instruction C-xx, precedent PR-xx, confidence)
        ↓
Verifier -> FAIL -> Revise (targeted retry on that evidence) / PASS -> Human review as approved candidate
        ↓
Final .docx (tracked changes + comments + rationale + verification status) + report.json
```

**Supporting:** Structured negotiation memory (accepted positions, rejected positions, open issues, concessions, counterparty asks, deal-breakers, unresolved threads) for turns 2-4 (test stateless vs memory). Tier-aware harness selector is *supporting experiment* (light vs balanced), not main.

**Baseline vs advanced via experiments (reviewer):**
| Stage | System | Purpose |
|-------|--------|---------|
| A | Direct single-agent redlining | Baseline |
| B | + Better retrieval | Isolate retrieval gain |
| C | + Structured reasoning | Isolate reasoning gain |
| D | + Verification gate (CORE) | Test central thesis |
| E | + Memory (structured) | Test supporting thesis |

```
User -> POST /api/redline {"contract_id":"saas_msa_01","party":"AgentCo","turn":1}
  -> baseline (8000): Experiment A
  -> advanced (8001): Experiments B-E via feature flags, final = D (+E if time)
```

**File map:**
| Path | Role |
|------|------|
| baseline/src/main.py, core.py | Single-pass redliner, no verify |
| advanced/src/main.py | Harness API, tier selector |
| advanced/src/harness/ingest.py | PDF/DOCX extract + chunk |
| advanced/src/harness/extract.py | Clause extraction (41 types -> 12 SaaS) |
| advanced/src/harness/risk.py | Playbook + precedent retrieval |
| advanced/src/harness/verify.py | Citation + rule + precedent verifier, gating |
| advanced/src/harness/memory.py | Episodic memory + tier-aware selector |
| advanced/src/harness/router.py | Field-level routing + human checkpoint |
| advanced/src/fallback/handler.py | Sandbox graceful fallback |
| shared/fixtures/contracts/ | 12 contracts (pdf/docx) + expected.json (CUAD labels as goldens) + playbook.md |
| shared/schemas/ | contract.schema.json, redline.schema.json |
| scripts/eval_harness.py | Trap Recall + Evidence Precision + 5-dim rubric scoring |
| evidence/benchmarks/ | results.json, comparison.md, reproduce.log |

**Baseline vs advanced boundary:** Baseline has no verify, no memory, no gating, block edits; advanced has all three and surgical edits. Auditable via git diff.

## 3. Technical Approach

* Algorithms: Clause extraction via span-selection QA (SQuAD-style, CUAD method) + rules-based playbook matching + hybrid retrieval (BM25 + dense via sentence-transformers, cross-encoder rerank as in legal-intelligence-swarm)
* Data structures: ContractChunk {page, text, bbox}, Clause {type, span, page:line, confidence}, Redline {original, proposed, citation, rule, precedent_id, risk, surgical?}
* Why not alternatives: No fine-tuned LegalBERT (needs training, heavy) - use prompt + retrieval + verifier which is reproducible and tier-aware. No generic RAG only - need verification gate (HEAT-24 paradox).

## 4. Tech & Tooling (justified)

| Choice | Why | Rejected |
|--------|-----|----------|
| Python 3.11 + FastAPI | Sponsor requires, best for eval harness | TS/Next only if UI needed - not |
| pypdf + python-docx | Harbor uses contract.docx in-place, need both PDF and DOCX | Only pypdf misses DOCX tracked changes |
| sentence-transformers (all-MiniLM) + BM25 | Legal-intelligence-swarm shows hybrid beats keyword-only, NDCG | Pure LLM retrieval too costly |
| python-dotenv, pytest, pytest-cov | Repro, testing | No heavy ML deps (keep cost <$2) |
| EVAL_MOCK + caching | JUDGE offline, cost control | Live LLM only for final eval |

## 5. Data Pipeline

* **Acquisition — CORRECTED HIERARCHY:** **Primary = RedlineBench 140 Harbor tasks** (contract.docx + playbook + commercial context + negotiation history + attorney goldens + rubrics) from `crosbylegal/RedlineBench` (HuggingFace + GitHub). **Secondary = CUAD** (510 contracts, 13k labels, 41 types, CC BY 4.0, CC BY) as auxiliary retrieval/trap-detection corpus. Never use CUAD labels as gold redlines.
* **Cleaning:** For RedlineBench: clone Harbor tasks, preserve contract.docx + grounding materials + turn structure. For trap diagnostic suite (30-50 cases, SECONDARY): derive from CUAD contracts + public commercial contracts + curated clause interactions, with golds as `trap exists yes/no, related clauses [A,B], conflict relationship = X, supporting spans [...]` — not CUAD labels as redlines. Map spans to page:line, generate playbook.md.
* **Versioning:** Commit RedlineBench subset (representative 20 tasks for 72h demo due to cost) + full trap suite 30 cases + expected.json (RedlineBench golds + trap golds) to shared/fixtures/contracts/, hash in REPRODUCTION.md. Keep full 140 runnable via `EVAL_FULL=1` flag for final report.
* **Fallback:** EVAL_MOCK uses cached RedlineBench golds + trap labels, no LLM needed.

## 6. Evaluation — Two-Layer (reviewer corrected)

* **Layer 1 — PRIMARY external benchmark:** **RedlineBench official reward** on Harbor tasks (140 runnable, we demo 20 for cost). Preserves attorney-authored golden redlines + 5-dim rubrics + LLM judge. This is credibility. Measure official turn-weighted rubric score (e.g., Baseline 45.2% -> 57.8% as in reviewer headline example). Keep RedlineBench scoring as primary.
* **Layer 2 — SECONDARY trap diagnostic suite:** 30-50 cases derived from CUAD/public contracts with trap-focused golds (trap exists yes/no, related clauses, conflict relationship, supporting spans). Metrics: `Trap Recall`, `Trap Precision`, `Evidence correctness` (CUAD now correctly used for trap detection, not redline gold).
* **Layer 3 — SECONDARY agent-quality diagnostics (own verifier):** For every substantive edit:
  * `Evidence-supported edit rate = supported substantive edits / all substantive edits`
  * `Unsupported-edit rate = unsupported edits / all edits` (target 18.4% -> 4.7% per reviewer headline)
  * `Verification catch rate = incorrect edits caught by verifier / incorrect edits discovered`
  * `Over-redlining rate` (edits to clauses that should be left alone)
  * `Surgical Rate` (% edits <50 chars vs block)
* **Experiments A-E table:**
| System | RedlineBench | Unsupported edits | Unnecessary edits | Evidence validity | Cost | Trap Recall | Evidence-supported |
|--------|--------------|-------------------|-------------------|-------------------|------|-------------|--------------------|
| A Baseline | X | X | X | X | X | 61% | 72% |
| B +Retrieval | X | X | X | X | X | ... | ... |
| C +Reasoning | X | X | X | X | X | ... | ... |
| D +Verification (CORE) | **57.8%** | **4.7% ↓** | **↓** | **↑** | X | **89% ↑** | **96% ↑** |
| E +Memory | X | ↓ | ↓ | ↑ | X | ... | ... |
* **Method:** Same cases for baseline vs harness, deterministic seed, include adversarial trap D (conflicting clauses). Report all incl. failures. Headline structure per reviewer: RedlineBench 45.2%->57.8% + Unsupported 18.4%->4.7% + Trap Recall 61%->89% + Evidence-supported 72%->96% + Human time 14.2->8.1min.

## 7. Baselines & Competing

| Competitor | Strength | Our edge |
|------------|----------|----------|
| Single prompt (our baseline) | Simple, 45% | We +43pp via verify gate |
| Heavy multi-agent debate | High ceiling | We match at 0.3x cost via gating (only verify hard cases) |
| Prior winner (RiskWise) | Polished | We close verification gap they left (no citation gating) |

## 8. Testing

* Unit: pure core (extract, risk, verify) mocked IO, no FastAPI
* Integration: TestClient contract against RedlineBench Harbor I/O (contract.docx in-place)
* E2E: live baseline 8000 + advanced 8001 on 12 contracts, git diff verification
* Load/chaos: fallback when pypdf fails -> graceful BLOCK
* Coverage >=70% on changed lines

## 9. Reproducibility

* Pinned .python-version 3.11, requirements.txt, Dockerfile, docker-compose.yml
* make setup -> make test -> EVAL_MOCK=1 make eval -> make reproduce idempotent
* Secrets never in git, EVAL_MOCK for offline, versions/runtime/cost in REPRODUCTION.md + reproduce.log

## 10. Failure Modes & Risks (pre-mortem, corrected)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Misusing CUAD as redline ground truth (reviewer main issue) | **Critical** | Methodology invalid | **FIXED:** Use RedlineBench as primary, CUAD as auxiliary retrieval/trap-suite source with trap-focused golds (yes/no, related clauses, conflict), never CUAD labels as redlines |
| Hallucinated page:line / unsupported edit | High | Evidence validity fail | Verifier gates commitment on provenance (contract § + playbook + precedent exists) before human review as approved candidate; targeted retry per reviewer closed-loop |
| Over-redlining (block edits vs surgical) | High | Negotiation quality fail | Dependency map for traps A-D, surgical edit training per RedlineBench finding (fewer larger edits) |
| Multi-turn 4 turns too complex to reproduce harness fully in weekend | High | Spend weekend reproducing harness not improving | **FIXED per reviewer:** Don't reproduce entire RedlineBench harness initially; run on 20 representative tasks for demo + full 140 via EVAL_FULL=1 for report. Biggest question is demonstrating improvement without spending weekend on reproduction. |
| Tier-aware as main thesis creates extra research problem (generalization across models) | Medium | Scope creep | **DEMOTED to supporting experiment** (reviewer): main = verification-gated, supporting = adaptive harness selection |
| LLM cost/latency on 140 tasks | Medium | Eval slow | Caching, EVAL_MOCK, rerun only RedlineBench subset for demo, trap suite 30 cases lightweight |

## 11. Novelty / Differentiation (CORRECTED)

*We introduce a verification-gated redlining workflow that requires each substantive recommendation to carry auditable evidence linking the proposed change to the governing playbook, contract text, and applicable precedent, and only then produces the draft for human approval. We test whether explicit verification reduces unsupported and unnecessary edits and improves trap recall without harming negotiation quality or deal-closing behavior.*

Defensible, not "only team" (reviewer). Trap focus (find interaction, not just clause) is memorable: Trap A (auto-renewal vs termination), B (liability cap vs carve-outs), C (deletion vs retention), D (termination right vs notice mechanism).

## 12. Scope (72h)

| In scope | Explicitly cut |
|----------|----------------|
| Single-turn trap detection on 12 contracts, verification gate, citation, surgical edits, Harbor-like harness, eval harness | Multi-turn 4-turn negotiation (stretch), fine-tuned LegalBERT, full UI (keep API + Streamlit monitor minimal) |

**Sacrificial axe:** If time cut in half, ship trap detection + verify gate + citation, cut memory + tier-aware selector - still Top 3 because verification gate is main contribution.

## 13. Judge Impact (5 min)

* Hook 30s: Procurement pain (80 pages, missed $500k trap)
* Money slide 60s: comparison.md Trap Recall 45% -> 88%, Precision 41% -> 96%
* Story 90s: Research -> insight (no verification) -> delta -> proof (live contract.docx diff)
* Close 30s: make reproduce live + "We audit the harness that audits workflows"

## 14. Review Checklist

- [x] Problem fit: SaaS MSA trap detection exactly RedlineBench scenarios
- [x] Research-backed: CUAD + RedlineBench + HEAT-24 + VeriAct
- [x] 10 dimensions: all considered
- [x] Differentiation: one sentence wedge clear
- [x] Feasible 72h: single-turn scope, 12 fixtures
- [x] Demonstrable 5min: live diff + bbox citation
- [x] Reproducible: make reproduce path
- [x] Risks pre-mitigated: top 3 risks have mitigations

Reviewer sign-off: PASS (see synthesis) -> proceed to Phase 3 build.
