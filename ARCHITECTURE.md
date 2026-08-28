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

## 5. Stack decisions (pre-kickoff defaults, override if PDF prescribes)

| Layer | Default | Reason | When to switch |
|-------|---------|--------|----------------|
| Baseline | Python 3.11 + FastAPI | Fastest to correctness; best test tooling | PDF says TS/Java/Go/Rust — use that |
| Advanced | Same stack + LangGraph / retry / cache | Easy delta on top of baseline | If baseline switches, advanced follows |
| Frontend (if needed) | Next.js 14 | Judges expect polished demo | Only if problem has UI |
| DB | SQLite (file) or in-memory | Zero-setup repro | PDF says Postgres/Redis — use Docker service |
| Infra | Docker Compose | One-command repro for judges | — |

**Rule:** Never introduce a stack the problem doesn't need. Prize is for *engineering quality*, not tech sprawl.

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

## 7. What to decide at kickoff (T+0 checklist — Phase 0 gate)

- [ ] Problem type: API / pipeline / agent / UI / data?
- [ ] Starter repo exists? Clone into `starter/` and note delta in §8
- [ ] Runtime pinned by PDF? Update `Makefile`, `.python-version`, `REPRODUCTION.md`, Docker
- [ ] Dependency limits? Enforce in `requirements.txt` / `package.json`
- [ ] Network allowed? If not, add offline fixtures to `shared/fixtures/`
- [ ] Acceptance tests location? Wire into `tests/e2e/` + `scripts/eval.py`
- [ ] **Directive gates:** `docs/10-RESEARCH-PROTOCOL.md` launched? `docs/11-IMPLEMENTATION-PLAN.md` template copied? `docs/20-REVIEW-RUBRIC.md` understood by reviewer?

> Per Directive: no `baseline/` implementation begins until this checklist is committed.

---

## 8. Starter Repo Delta (fill at kickoff if provided)

| File from starter | Kept | Modified | Added | Reason |
|-------------------|------|----------|-------|--------|
| _(example) `starter/app.py` |  |  |  |  |

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
