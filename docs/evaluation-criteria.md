# Evaluation Criteria — Mapping to Evidence (Official Rubric)

> **Source:** `PROBLEM.md` §5 — official judging rubric (100 pts) from the micro1
> Agentic Workflows Hackathon. This page maps each dimension to the evidence that
> backs it.

## Qualification Gate (implicit — before scoring)

| Check | How we satisfy | Evidence |
|-------|---------------|----------|
| Eligibility | Individual, open globally (18+, not micro1/judge/household), one submission (latest counts) | registration |
| Completeness | Four deliverables present (code+changelog, reproduction guide, video, trajectories) | `README.md` + `CHANGELOG.md` + `REPRODUCTION.md` + `evidence/` |
| Integrity | Licences respected, what-existed vs added clear, no secrets, ethical use, public/synthetic data | `ARCHITECTURE.md` §8 + `.env.example` |
| Trace | Agent trajectories for every agent with instructions→result | `evidence/trajectories/` + `.agent/instructions/` |
| Reproducibility | Clean-env path documented and runnable | `REPRODUCTION.md` + `make reproduce` |

**Fail any → not scored.**

## Official Rubric — 6 Dimensions (100 pts)

| # | Criterion | Pts | What strong (from PDF) | Self-check | Our evidence |
|---|-----------|-----|------------------------|------------|--------------|
| 1 | **Problem & User Value** | **15** | Meaningful problem for a clearly defined user | *Who has the bottleneck and why does solving it matter?* | `README.md` (user/bottleneck/value) + `docs/problem-brief.md` + `PROBLEM.md` §1, §8 examples |
| 2 | **Agent Solution & Engineering** | **30** | Uses agents **purposefully**, technically sound; context/tools/memory/verification/skills/orchestration only if they help | *Which design choices helped the agent solve the problem?* | `baseline/` vs `advanced/` + `advanced/src/verify.py`, `cache.py`, `fallback/` + `docs/11-IMPLEMENTATION-PLAN.md` + `ARCHITECTURE.md` |
| 3 | **End-to-End Quality** | **20** | Realistic, self-contained execution; result a user could use / sign their name to, not an obvious AI draft | *Would the user consider this high quality or clearly AI-generated?* | `tests/e2e` + `advanced/tests` + polish, error handling, explainability |
| 4 | **Measured Improvement** | **15** | Fair baseline, same cases, changelog connects each iteration to evidence | *Which changes truly improved the outcome?* | `evidence/benchmarks/comparison.md` + `CHANGELOG.md` + `scripts/eval_harness.py` (30 small tests due to free-tier limits, incl. one hard) |
| 5 | **Reproducibility** | **15** | Another person can run solution + baseline and reach main result from clean env | *Could they from a clean environment?* | `REPRODUCTION.md` + `make reproduce` + `evidence/benchmarks/reproduce.log` + pinned versions |
| 6 | **Hot Take / Insights** | **5** | Observed failure → practical lesson for more reliable agents | *What did you learn and how would it change next build?* | `CHANGELOG.md` 🗑️ entry + `README.md` Hot Take + `evidence/benchmarks/` |

**Weight order:** 2 (30) ≫ 3 (20) ≫ 1/4/5 (15) ≫ 6 (5). When time-constrained, prioritize in that order — but Top 3 requires strength across all six.

## How to Maximize (1st-place tactics)

- **Problem & User Value (15):** Name a real user, concrete bottleneck, and value in seconds (the 1-paragraph test from Directive Phase 0). Avoid artificial or overly broad problems.
- **Agent Solution (30):** Smallest purposeful set — every agent/tool/skill must have a measurable purpose. Purposeful > numerous (PDF §2). Ground choices in Phase 2 research, not hype.
- **End-to-End (20):** One realistic execution start-to-finish, polished, explains its work, handles edge cases gracefully. Demo shows this live, not slides.
- **Measured Improvement (15):** Define primary metric before optimizing; same 10+ cases for baseline + agent; report *all* results incl. failures; changelog ties each kept/removed change to +/− delta.
- **Reproducibility (15):** Hostile-clone drill before submission (Directive Phase 8): `git clone` → `cp .env.example .env` → `make reproduce`. Document exact commands, data, versions, runtime, cost.
- **Hot Take (5):** One genuine insight from a failure you observed and fixed (or explicitly scoped), not a generic platitude.

## Internal Scorecard (use before submission — Directive Phase 11)

| Criterion | Max | Current assessment | Evidence | Remaining gap |
|-----------|-----|--------------------|----------|---------------|
| Problem & User Value | 15 | | | |
| Agent Solution & Engineering | 30 | | | |
| End-to-End Quality | 20 | | | |
| Measured Improvement | 15 | | | |
| Reproducibility | 15 | | | |
| Hot Take / Insights | 5 | | | |
| **Total** | **100** | | **conservative — evidence required** | |

> Award points only with convincing evidence. Be conservative — judges will be.

## Self-Check Before Ship (from PDF, per criterion)

- 15 — *Who experiences the bottleneck and why does solving it matter?*
- 30 — *Which design choices helped the agent solve the problem?*
- 20 — *Would the user consider this high quality, or clearly AI-generated?*
- 15 — *Which changes truly improved the outcome?*
- 15 — *Could they do it from a clean environment?*
- 5 — *What did you learn and how would it change what you build next?*

If any answer is weak, it is **MUST FIX** per `docs/20-REVIEW-RUBRIC.md`.
