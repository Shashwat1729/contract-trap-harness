# Evaluation Criteria — Mapping to Evidence (10 Dimensions)

> Scored **out of 100** after a strict qualification gate. The brief reveals 4 pillars via tie-break; this doc maps them to the **10 competition dimensions** from the Execution Directive — because 1st-place teams optimize for all 10.

## Qualification Gate (MUST pass before scoring — per brief)

| Check | How we satisfy | Evidence |
|-------|---------------|----------|
| Eligibility | Individual, 18+, one submission | registration + README |
| Completeness | All submission package files present | `docs/submission-checklist.md` |
| Integrity | Original work, licences respected, no secrets | `ARCHITECTURE.md` §8 delta table + `.env` not committed |
| Trace | Agent trajectories submitted | `evidence/trajectories/` + `.agent/instructions/` |
| Reproducibility | Clean-env run succeeds | `make reproduce` green + `REPRODUCTION.md` |

**If any gate fails → disqualified before rubric scoring. This is non-negotiable.**

## Rubric — 4 Pillars (from brief) → 10 Dimensions (from Directive)

| Pillar (tie-break order) | Likely weight | Maps to Directive dimensions | What judges look for | Our evidence |
|--------------------------|---------------|------------------------------|----------------------|--------------|
| **1. Agent Solution & Engineering** | ~35 | 2 Technical depth, 3 Novelty, 5 Execution quality, 9 Scalability | Correctness, edge cases, failure modes, technical judgment, sandboxing, human-in-loop | `baseline/tests` + `advanced/tests` + `advanced/src/fallback/` + `ARCHITECTURE.md` + `docs/research/` |
| **2. Reproducibility** | ~25 | 5 Execution quality, 8 Documentation, 10 Judgeability | Clean-env setup, pinned versions, Docker, exact commands, cold-clone drill | `REPRODUCTION.md` + `make reproduce` + `docker-compose.yml` + `evidence/benchmarks/reproduce.log` |
| **3. Measured Improvement** | ~25 | 3 Novelty, 6 Evidence, 10 Judgeability | Baseline vs advanced with **numbers**, not cosmetics; ≥2 axes | `evidence/benchmarks/comparison.md` + `CHANGELOG.md` + `scripts/eval.py` |
| **4. End-to-End Quality** | ~15 | 1 Relevance, 4 Impact, 7 Demo, 8 Documentation, 10 Judgeability | README clarity, video, trajectory readability, polish, real-world potential | `README.md` + `docs/video-script.md` + `evidence/trajectories/` + `docs/00-EXECUTION-DIRECTIVE.md` |

### The 10 dimensions in full (Directive §3)

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

**Every major decision must increase at least one dimension without harming another.** The 9-lens review in `docs/20-REVIEW-RUBRIC.md` enforces this.

## How to Maximize Each Pillar (1st-place tactics)

- **Engineering (tie-break #1):** Contract tests on Day 1 against *every* acceptance test. Log every failure mode in `ARCHITECTURE.md` §6. Show human checkpoint in trajectories.
- **Reproducibility:** Never say "it works on my machine" — `make reproduce` is the contract. Run the hostile-clone drill (`git clone` → `make reproduce`) before the final hour (Directive Phase 4).
- **Measured Improvement:** The advanced delta must be **≥2 axes** and visible in `comparison.md` at a glance. One axis = reviewer flags "cosmetic" → `FAIL` (risk per brief: "not a cosmetic variation").
- **E2E Quality:** Video ≤4:30 live execution (not slides); README one paragraph per required prompt (user/bottleneck/value/changelog/failure/hot-take); trajectories show retries + checkpoints; research-backed novelty wedge stated in one sentence.

## Tie-Break Order (from brief)

1. Higher Agent Solution & Engineering
2. Higher Reproducibility
3. Higher Measured Improvement
4. Higher End-to-End Quality
5. Final panel review of documented evidence

→ **Implication:** If short on time, prioritize pillars in exactly this order (and within, prioritize dimensions 1→10). That is the directive.

## Self-Check Before Submission

Ask per dimension: *"If a skeptical reviewer attacked this dimension alone, would we survive?"* If any dimension scores ≤2/5 in `docs/20-REVIEW-RUBRIC.md`, it is **MUST FIX** — loop again through `Review → Fix → Test → Reproduce → Review`.
