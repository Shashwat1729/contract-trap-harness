# Evaluation Criteria — Mapping to Evidence

> Based on brief parsing. Scored **out of 100** after strict qualification gate. Tie-break reveals 4 pillars.

## Qualification Gate (must pass before scoring)

| Check | How we satisfy | Evidence |
|-------|---------------|----------|
| Eligibility | Individual, 18+, one submission | registration + README |
| Completeness | All submission package files present | `docs/submission-checklist.md` |
| Integrity | Original work, licences respected, no secrets | `ARCHITECTURE.md` §8 delta table + `.env` not committed |
| Trace | Agent trajectories submitted | `evidence/trajectories/` + `.agent/instructions/` |
| Reproducibility | Clean-env run succeeds | `make reproduce` green + `REPRODUCTION.md` |

**If any gate fails → disqualified before rubric scoring.**

## Rubric (100 points — inferred breakdown, update at kickoff if PDF gives weights)

| Pillar (tie-break order) | Likely weight | What judges look for | Our evidence |
|--------------------------|---------------|----------------------|--------------|
| **1. Agent Solution & Engineering** | ~35 | Correctness, edge cases, failure modes, technical judgment, sandboxing, human-in-loop | `baseline/tests` + `advanced/tests` + `advanced/src/fallback/` + `ARCHITECTURE.md` |
| **2. Reproducibility** | ~25 | Clean-env setup, pinned versions, Docker, exact commands | `REPRODUCTION.md` + `make reproduce` + `docker-compose.yml` |
| **3. Measured Improvement** | ~25 | Baseline vs advanced with numbers, not cosmetics | `evidence/benchmarks/comparison.md` + `CHANGELOG.md` + `scripts/eval.py` |
| **4. End-to-End Quality** | ~15 | README clarity, video, trajectory readability, polish | `README.md` + `docs/video-script.md` + `evidence/trajectories/` |

## How to maximize each pillar

- **Engineering:** Contract tests on Day 1 against every acceptance test. Log every failure mode in `ARCHITECTURE.md` §6.
- **Reproducibility:** Never say "it works on my machine" — `make reproduce` is the contract. Test it on a fresh clone.
- **Measured Improvement:** The advanced delta must be ≥2 axes and visible in `comparison.md`. One axis = reviewer flags "cosmetic."
- **E2E Quality:** Video ≤5 min, timed script; README one paragraph per required prompt; trajectories show retries + checkpoints.

## Tie-break order (from brief)

1. Higher Agent Solution & Engineering
2. Higher Reproducibility
3. Higher Measured Improvement
4. Higher End-to-End Quality
5. Final panel review

→ Implication: if short on time, prioritize pillars in this order.
