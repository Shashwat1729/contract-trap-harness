# Project Execution Directive — Frontier Engineering Challenge 2026

> **Status:** Active (pre-kickoff → submission)  
> **Objective:** Top 3 minimum, **1st place target**. Every decision is judged against that bar.  
> **Authority:** This document overrides all prior planning notes. Treat it as the single source of truth until `PROBLEM.md` is ingested; after ingestion, `PROBLEM.md` is primary and this directive is the *process* that executes it.

---

## 1. Governing Principle

Assume judging is **extremely critical** and competition quality is **elite**. Optimizing for "working" guarantees mid-pack. Optimizing for **demonstrably superior engineering** is the only path to Top 3.

**Non-negotiable rule:** No implementation begins until documentation, scaffolding, and research backbone are complete. Premature coding is the fastest way to build the wrong thing well.

---

## 2. Execution Phases (sequential gates — do not skip)

### Phase 0 — Problem Verification & Scaffolding
*Trigger: `PROBLEM.md` ingested at kickoff (Aug 28 15:00 UTC)*

- Verify full repo structure against the problem statement (files, runtime, deps, starter repo, constraints, acceptance tests).
- Complete all required documentation shells: `docs/problem-brief.md`, `ARCHITECTURE.md` §§7–8, `REPRODUCTION.md` env pins, `shared/schemas`, `tests/e2e` contract.
- Outcome: `make reproduce` runs (even if baseline is stub), no missing-file surprises on Day 3.

**Gate:** `docs/problem-brief.md` signed + `ARCHITECTURE.md` T+0 checklist fully checked.

### Phase 1 — Deep Research (mandatory before planning)
Go **far beyond** surface web searches. Cover in parallel:

| Track | Sources | What to extract |
|-------|---------|-----------------|
| **Papers & technical pubs** | arXiv, Semantic Scholar, conference proceedings | SOTA techniques, theoretical limits, proven architectures |
| **Open-source** | GitHub (stars, issues, PRs), Hugging Face, Awesome lists | Implementation patterns, failure modes, scaling gotchas |
| **Engineering writing** | Company blogs, benchmark reports, case studies | Real-world trade-offs, cost/latency numbers |
| **Community signal** | Reddit, HN, Discord, expert Twitter/X | What practitioners actually struggle with, hype vs. reality |
| **Competitive landscape** | Prior hackathon winners, product teardowns | Differentiation gaps — what *obvious* solution will 80% of teams build? |

For each finding, record:
- Approach / technique
- Limitations & failed attempts (equally valuable)
- Evaluation methodology used
- Opportunity for us to do 10× better on *one* axis

**Artifact:** `docs/10-RESEARCH-PROTOCOL.md` + `docs/research/NNN-<topic>.md` per thread. No research → no plan review.

### Phase 2 — Research-Backed Implementation Plan
Produce `docs/11-IMPLEMENTATION-PLAN.md` containing:

1. **Proposed solution & fitness** — why this solves the *actual* problem, not a proxy.
2. **System architecture & project structure** — diagram + file map, baseline vs. advanced boundary.
3. **Core technical approach** — algorithms, models, key data structures, why not alternatives.
4. **Technology & tooling** — stack choices with justification (and what was rejected).
5. **Data requirements & pipeline** — acquisition, cleaning, synthetic/fallback, versioning.
6. **Evaluation methodology & success metrics** — quantitative, with baselines and statistical rigor.
7. **Baselines & competing approaches** — what we beat and by how much.
8. **Testing & validation strategy** — unit → integration → e2e → load / chaos.
9. **Reproducibility requirements** — pinned versions, Docker, `make reproduce` contract.
10. **Failure modes, risks, mitigations** — pre-mortem, not post-mortem.
11. **Novelty / differentiation** — the one sentence a judge remembers.
12. **Hackathon-realistic scope** — what ships in 72h vs. what is explicitly cut.
13. **Judge impact** — what makes this *stand out* in 5 minutes.

**Critical:** Do not treat v1 as final. Critically review against:
- Problem statement (does it solve the *asked* problem?)
- Research findings (is it SOTA or naive?)
- Judging criteria (does it maximize 10 dimensions in §4?)
- Feasibility (can 1 person + agents ship it?)
- Originality (would a strong competitor do this too?)
- Demo potential (can it be shown, not just described?)

Refine until coherent, defensible, technically strong, and executable. Record rejections in `docs/architecture-decisions.md`.

### Phase 3 — Disciplined Implementation
- Maintain agreed structure; no ad-hoc folders.
- Incremental slices — each slice = runnable + tested + logged in `CHANGELOG.md` + committed.
- Tests alongside code, not after. Experiments tracked in `evidence/benchmarks/`.
- Technical decisions documented immediately (`ARCHITECTURE.md` / ADR).
- Reproducibility guarded — any manual step is a bug.
- Continuous alignment check: "Does this still solve `PROBLEM.md` as written? As researched?"

### Phase 4 — Reproduction Dry Run (from clean state)
Pretend you are a hostile third-party reviewer who has never seen the repo. Run:

```
git clone <url> && cd micro1-front && cp .env.example .env && make reproduce
```

Hunt for:
- Missing deps, outdated docs, undocumented config, broken setup, non-reproducible runs, hard-coded paths/secrets, missing data/assets, test flakes, perf cliffs, inconsistent results, demo-breaking edge cases.

Fix, re-run until `make reproduce` is idempotently green. Then commit the validated state.

### Phase 5 — Final Review Loop (ruthless, multi-lens)
Review repeatedly through 9 lenses:

| Lens | Question |
|------|----------|
| **Technical reviewer** | Is the engineering genuinely strong? |
| **Research reviewer** | Is methodology sound & evidenced? |
| **Hackathon judge** | Would this score Top 3 today? |
| **Competitor** | What would a better team do? |
| **Skeptic** | Which claims are weak / unproven? |
| **End user** | Is it useful & intuitive? |
| **Demo judge** | Is value clear in < 3 minutes? |
| **Repro reviewer** | Can a stranger reproduce it cold? |
| **Security / reliability** | What fails in production? |

Triage each finding: **Must fix / Should fix / Nice to have / Safe to leave**. Fix all Must + high-impact Should, then loop:

`Review → Identify → Prioritize → Fix → Test → Reproduce → Review again`

Stop only when no high-impact weakness remains.

### Phase 6 — Final Gate (honest)

> **If submitted to a highly competitive hackathon today, is there a credible reason judges would place this in Top 3?**

Then the harder question:

> **What specifically prevents it from being #1?**

If fixable, fix it and re-enter Phase 5. Goal is not "finished" — goal is **technically rigorous, research-backed, reproducible, differentiated, polished, judge-friendly, and credible for 1st.**

---

## 3. Competition Standard — The 10 Dimensions

Optimize for all 10. A 9/10 product with a 5/10 story loses to an 8/10 product with a 10/10 story.

1. **Problem relevance** — Important, clearly defined, worth solving.
2. **Technical depth** — Real engineering/research substance, not glue code.
3. **Novelty** — Clear differentiation from obvious / existing solutions.
4. **Impact & usefulness** — Value is immediate and undeniable.
5. **Execution quality** — Robust, clean, reproducible.
6. **Evidence** — Claims are proven with numbers/logs, not adjectives.
7. **Demo quality** — Sophistication is *shown* convincingly.
8. **Documentation & presentation** — Judge can grasp problem → solution → architecture → results → differentiation in minutes.
9. **Scalability & real-world potential** — Beyond a hackathon prototype.
10. **Judgeability** — Strongest aspects are demonstrable within limited judging time.

**Every major decision must increase at least one dimension without harming another.**

---

## 4. Anti-Patterns (auto-fail)

- Starting code before research + plan are reviewed.
- Single-pass "vibe coding" with no eval harness.
- Cosmetic advanced variation (same logic, new styling) — disqualification risk per brief.
- Claims without `evidence/` links.
- Manual, undocumented setup steps.
- Secrets or PII in git.
- Video > 5 min or slideware instead of live execution.
- One review pass and ship.

---

## 5. Traceability

Each phase leaves artifacts that judges can audit:

```
Phase 0 → PROBLEM.md + docs/problem-brief.md + ARCHITECTURE.md §7–8
Phase 1 → docs/research/*.md + docs/10-RESEARCH-PROTOCOL.md
Phase 2 → docs/11-IMPLEMENTATION-PLAN.md + docs/architecture-decisions.md
Phase 3 → baseline/ + advanced/ + CHANGELOG.md + tests/
Phase 4 → evidence/benchmarks/reproduce.log + make reproduce green
Phase 5 → docs/20-REVIEW-RUBRIC.md (filled)
Phase 6 → final gate sign-off in CHANGELOG.md + README hot take
```

No phase is "done" until its artifacts exist and are committed.

---

*This directive is binding for all contributors (human + agents) until submission.*
