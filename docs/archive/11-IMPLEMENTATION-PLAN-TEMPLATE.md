# Implementation Plan — Template (Research-Backed)

> Copy this template to `docs/11-IMPLEMENTATION-PLAN.md` at kickoff and fill it.  
> It *is* the implementation — if it's weak, the build will be weak. Review it ruthlessly before coding (Directive Phase 2).

---

## 0. Meta

- **Date:** 2026-08-__
- **Problem statement ref:** `PROBLEM.md` §__ + `docs/problem-brief.md`
- **Research refs:** `docs/research/00-synthesis.md`, tracks A–E
- **Status:** Draft / In Review / Approved (Reviewer sign-off: ___)

---

## 1. Proposed Solution & Fitness

*One paragraph: what we build and why it's the *right* answer to the *actual* problem (not a proxy). Tie to a specific constraint in `PROBLEM.md`.*

**Why not the obvious alternative?** *(One paragraph — the thing 80% of teams will do and why it loses.)*

---

## 2. System Architecture & Project Structure

**Diagram (text OK):**
```
[Client/UI] → [Advanced Gateway: verify+retry+cache] → [Core Engine]
                     ↘ fallback/sandbox ↗
[Basis: baseline/] → [shared/schemas] → [evidence/benchmarks] → [eval.py]
```

**File map:**
| Path | Responsibility |
|------|---------------|
| `baseline/` | Stub baseline (acceptance-test green, no cleverness) |
| `advanced/` | Delta: verify, retry, cache, fallback, observability |
| `shared/` | Schemas, fixtures, utils (true shared only) |
| `scripts/eval.py` | Deterministic harness — metrics pinned below |
| `evidence/` | Every number the README cites |

**Baseline vs. advanced boundary:** *One sentence that makes the delta auditable.*

---

## 3. Core Technical Approach

- **Algorithms / models:** *e.g., verifier LLM (calibrated), retrieval-augmented correction, deterministic fallbacks.*
- **Key data structures & flows:** *sequence diagram for the critical path.*
- **Why not alternatives:** *table — alternative / why rejected (cost, latency, accuracy, reproducibility).*

---

## 4. Technology & Tooling (with justification)

| Choice | Why | Rejected alternative & why |
|--------|-----|----------------------------|
| Python 3.11 + FastAPI | Fastest to acceptance-test green; best eval tooling | TypeScript/Next if problem is UI — switch per PDF |
| `advanced/src/verify.py` (small verifier) | +X% accuracy at 0.Y× cost vs. large verifier (paper ref) | Large verifier — cost cliff (cite) |
| Docker Compose | One-command repro for judges | — |

**Rule:** No stack is added because it's trendy. Every dep must pay for itself in a 10-dimension gain.

---

## 5. Data Requirements & Pipeline

- **Acquisition:** Public / synthetic / approved anonymous — never private/PII. If synthetic, generator script + seed committed.
- **Cleaning / versioning:** `shared/fixtures/` + `scripts/setup.sh` download; Git LFS if large; hash logged to `REPRODUCTION.md`.
- **Fallback for offline judging:** Offline fixtures + `EVAL_MOCK=1` path (judges can verify without keys/network).

---

## 6. Evaluation Methodology & Success Metrics

| Metric | Baseline | Target (Advanced) | Method | Tool |
|--------|----------|-------------------|--------|------|
| Success rate | 62% (mock) | ≥84% (+22pp) | Acceptance-test suite, deterministic seed | `scripts/eval.py` |
| p95 latency | 1.8s | ≤1.1s | 100-task run, cold start excluded | harness timer |
| Edge-case pass | 4/5 | 5/5 | Curated edge set | contract tests |
| Cost / 1k tasks | $0.42 | ≤$0.31 | Token log | evidence ledger |

**Statistical rigor:** Report *deltas* with n and seed; no cherry-picked single runs. Store raw logs in `evidence/benchmarks/`.

---

## 7. Baselines & Competing Approaches

| Competitor | Strength | Our edge |
|------------|----------|----------|
| Naive single-pass agent | Simple | We add verification + retry (paper-backed +Y%) |
| Heavy multi-agent debate | High ceiling | We match at Z% cost via caching (benchmark-backed) |
| Prior winner (2025) | Polished | We close gap X they left (issue #123) |

---

## 8. Testing & Validation Strategy

- **Unit** — pure `core.py` (no FastAPI), mocked IO.
- **Integration** — `TestClient` contract against `PROBLEM.md` acceptance tests.
- **E2E** — live `baseline` + `advanced` on `:8000/:8001`, real data.
- **Load / chaos** — p95 under N concurrent; fallback when dependency throttled.
- **Coverage gate:** ≥70% on changed lines; `make test-coverage` attached to `evidence/`.

---

## 9. Reproducibility Requirements

- Pinned `.python-version`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`.
- `make setup` → `make test` → `make eval` → `make reproduce` all idempotent.
- Secrets never in git (`.env.example` only); `EVAL_MOCK=1` for offline.
- Versions, runtime, cost logged in `REPRODUCTION.md` + `reproduce.log`.

---

## 10. Failure Modes, Risks, Mitigations (pre-mortem)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hidden rate-limited API | High | Blocks eval | Day 1 contract test + `advanced/src/fallback/` sandbox |
| Cosmetic delta flagged | High | Disqual risk | ≥2-axis delta enforced in `comparison.md`; reviewer gate |
| Non-reproducible submission | Medium | Disqual | Clean-clone drill before final hour |

---

## 11. Novelty / Differentiation

*One memorable sentence:* "We are the only team that **does X**, proven by **Y** (paper/benchmark), unlocking **Z** for the user."

*If you can't state it, you don't have it.*

---

## 12. Hackathon-Realistic Scope

| In scope (72h ship) | Explicitly cut (document why) |
|---------------------|-------------------------------|
| Baseline green + verify + retry + cache + eval harness | Multi-tenant auth, fine-tuned model training |

**Sacrificial axe:** If time cut in half, we ship ___ and cut ___ — still Top 3 because ___.

---

## 13. Judge Impact — Why It Stands Out in 5 Minutes

- **Hook (30s):** *Live* before/after on the hardest acceptance test (not slides).
- **Money slide (60s):** `comparison.md` with deltas — one glance, no explanation needed.
- **Story (90s):** Research → insight → delta → proof (the arc judges remember).
- **Close (30s):** `make reproduce` live.

---

## 14. Review Checklist (before coding)

- [ ] Problem fit — does it solve the *asked* problem exactly?
- [ ] Research-backed — every major choice cites a source/limitation?
- [ ] 10 dimensions — all 10 considered, none harmed?
- [ ] Differentiation — one-sentence wedge clear?
- [ ] Feasible in 72h — scope fits 1 person + agents?
- [ ] Demonstrable in 5 min — live demo, not theory?
- [ ] Reproducible cold — `make reproduce` path exists?
- [ ] Risks pre-mitigated — top 3 risks have mitigations?

**Reviewer sign-off:** `PASS / FAIL / BLOCKED` with evidence line refs. `FAIL` → iterate before any `baseline/` code.

---

*Template — Aug 28, 2026. Copy to `docs/11-IMPLEMENTATION-PLAN.md` at kickoff.*
