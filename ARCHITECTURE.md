# Architecture

> Decisions, trade-offs, and system design. Governed by [`docs/00-EXECUTION-DIRECTIVE.md`](docs/00-EXECUTION-DIRECTIVE.md) — no code before research + plan are reviewed.  
> Update at kickoff once the real problem is known. Pre-kickoff this records *why the scaffold is shaped this way* so you don't waste time re-deciding.

---

## 1. Why baseline/ + advanced/ are independent

**Decision:** Two fully independent services with `shared/` for common schemas/fixtures.

**Alternatives considered:**
- Single codebase with feature flags — simpler but judges want to run baseline alone; flags hide whether advanced is "cosmetic." Separate folders make the delta *obvious and diffable*.
- Monorepo with workspaces — good, but overkill before problem is known; we add it only if PDF prescribes Node + Python simultaneously.

**Trade-off:** Some duplication (`requirements.txt`, `Dockerfile`) is intentional — reproducibility > DRY at competition scope. `shared/` absorbs true duplication (schemas, fixtures, eval).

---

## 2. Reproducibility-first layout

- Every human action has a `make` target that logs to `evidence/`.
- `scripts/reproduce.sh` is the **single judge entrypoint** — mirrors exactly what `REPRODUCTION.md` says.
- Pinned versions + Docker give deterministic builds even if host Python/Node drift.
- `EVAL_MOCK=1` lets judges verify harness without real API keys (important for offline judging).

---

## 3. Evaluation harness design

```
tests/e2e  ─┐
baseline   ──┼─► scripts/eval.py ─► evidence/benchmarks/results.json
advanced   ──┘                      ─► evidence/benchmarks/comparison.md
```

- `scripts/eval.py` is **deterministic** (seeded, no flake) and **metric-agnostic** until kickoff — template metrics are success_rate, latency_p95, edge_pass, cost_per_1k.
- At kickoff, replace metrics with whatever the PDF/acceptance tests actually measure; eval.py is written to make that a 10-line edit.

---

## 4. Agent trajectory capture

- Instructions that shape each agent live in `.agent/instructions/` and `docs/agent-instructions.md` — these are part of the submission.
- Raw traces go to `evidence/trajectories/*.json` (captured via `scripts/capture_trajectory.sh` which wraps `opencode run --pure` or Codex/Cursor logs).
- Trajectories must show: instruction → actions → tool responses → feedback → retries → human checkpoints → final result. Capture script enforces this schema.

---

## 5. Stack decisions (final for Contract Trap Harness)

| Layer | Choice | Reason |
|-------|--------|--------|
| Baseline | Python 3.11 + FastAPI single-prompt redliner | Fastest to Harbor I/O (contract.docx in-place), best test tooling, matches scaffold |
| Advanced | Python 3.11 + FastAPI harness: ingest (pypdf+python-docx) + extract + risk (hybrid BM25+MiniLM) + verify gate + memory + router + fallback | Verification-gated commitments fix block-edit hallucination; tier-aware harness fixes HEAT-24 paradox; lightweight no fine-tune keeps <$2, <5min |
| Retrieval | sentence-transformers all-MiniLM-L6-v2 + BM25 (legal-intelligence-swarm pattern) | Hybrid beats keyword-only NDCG, 80MB not 2GB |
| Frontend | Minimal Streamlit Harness Monitor (optional, for demo) | Judges see 4 agents + live citations, not slides |
| DB | In-memory + JSON fixtures (CUAD committed), no Postgres | Zero-setup repro, EVAL_MOCK offline |
| Infra | Docker Compose | One-command repro for judges |

**Rule:** Never introduce a stack the problem doesn't need. Prize is for *engineering quality*, not tech sprawl.

Per docs/11-IMPLEMENTATION-PLAN.md §4: rejected fine-tuned LegalBERT (heavy training), rejected pure LLM retrieval (cost), rejected CrewAI (82% vs LangGraph 87% but we use lightweight harness, not full framework).

---

## 6. Failure modes already mitigated

| Failure mode | Mitigation in scaffold |
|--------------|------------------------|
| Hidden dependency / rate-limited API | `advanced/src/fallback/` stub + contract tests on Day 1 |
| Cosmetic-only advanced (disqualified) | `evidence/benchmarks/comparison.md` must show ≥2-axis delta |
| Non-reproducible submission | `make reproduce` tested on clean venv + Docker |
| Missing trajectories | `capture_trajectory.sh` runs on every agentic session |
| Video over 5 min | `docs/video-script.md` timed to 4:30 with chapter marks |

---

## 7. Kickoff Decisions (Phase 0 gate — DONE 2026-08-28)

- [x] Problem type: **Agentic contract redlining harness** (SaaS MSA, CUAD 41 types -> 12 SaaS, multi-turn 4-turn as stretch, single-turn trap detection core)
- [x] Starter repo: **No official starter**; reference `crosbylegal/redline-bench` (Harbor 140 tasks) + `TheAtticusProject/cuad` (510 contracts) cloned to docs/research/ for reference only
- [x] Runtime: Python 3.11 pinned (.python-version), Docker 24
- [x] Deps: pypdf, python-docx, sentence-transformers (light), FastAPI — pinned, <$2
- [x] Network: allowed but sandboxed; human approval gate (Rule 04/05); EVAL_MOCK for offline
- [x] Acceptance tests: Harbor I/O (contract.docx in-place) + 5-dim rubric + Trap Recall + Evidence Precision, wired to tests/e2e/ + scripts/eval.py
- [x] Directive gates: docs/10-RESEARCH-PROTOCOL.md done, docs/11-IMPLEMENTATION-PLAN.md approved, docs/20-REVIEW-RUBRIC.md understood

> Gate committed: docs/problem-brief.md + docs/research/00-synthesis.md + docs/11-IMPLEMENTATION-PLAN.md

---

## 8. Starter Repo Delta (Rule Book #2)

| File from starter | Kept | Modified | Added | Reason |
|-------------------|------|----------|-------|--------|
| No official starter | — | — | — | Greenfield harness, reference repos only |
| `crosbylegal/redline-bench` (ref only) | Cloned to docs/research/ for Harbor design reference | Not modified | — | Informed harness contract.docx + 5-dim rubric |
| `TheAtticusProject/cuad` (ref only) | Cloned to docs/research/ for 41 types | Not modified | — | Provided 13k labels for trap detection |

All files in baseline/, advanced/, shared/, scripts/, tests/, evidence/, docker-compose.yml, Makefile are **added by us** (see git log e63fd98, ddfa438, fe98474 + next).

> Rule-book requirement: "Make it clear what existed before the competition and what you added." This table is that proof.

---

## 9. Future ADRs (and Directive traceability)

Record significant reversals as ADRs in `docs/architecture-decisions.md`:

- ADR-001: Baseline/advanced split
- ADR-002: Evaluation metric choice (at kickoff)
- ADR-003: ... etc.

**Phase traceability (Directive §5):**
```
Phase 0 → PROBLEM.md + problem-brief.md + this §7–8
Phase 1 → docs/research/*.md + 10-RESEARCH-PROTOCOL.md
Phase 2 → 11-IMPLEMENTATION-PLAN.md + ADRs
Phase 3 → baseline/ + advanced/ + CHANGELOG.md
Phase 4 → evidence/benchmarks/reproduce.log
Phase 5 → docs/20-REVIEW-RUBRIC.md
Phase 6 → CHANGELOG final gate + README hot take
```
