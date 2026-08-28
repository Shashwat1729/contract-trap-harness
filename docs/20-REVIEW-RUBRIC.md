# Review Rubric — Ruthless Final Loop

> Use for Phase 5 (post-implementation) and Phase 6 (final gate).  
> Reviewer outputs `PASS / FAIL / BLOCKED` with evidence. No `PASS` without numbers.

Scoring: 0 (missing) → 5 (elite, 1st-place grade). Mark **MUST FIX** if ≤2 on any weighted dimension.

---

## 1. Qualification Gate (MUST be 5/5 before rubric scoring — per brief)

| Check | Evidence | Gate |
|-------|----------|------|
| Eligibility | Registration + solo submission | ☐ |
| Completeness | `README` + `CHANGELOG` + `REPRODUCTION` + `video` + `trajectories` present | ☐ |
| Integrity | Licences, delta table, no secrets | ☐ |
| Trace | Trajectories per agent, checkpoints visible | ☐ |
| Reproducibility | `make reproduce` green on clean clone | ☐ |

**If any ☐ → FAIL gate. Do not proceed to scoring.**

---

## 2. The 10 Dimensions (weighted — optimize for #1 first)

| # | Dimension | What 5/5 looks like | Score | Must-fix? |
|---|-----------|---------------------|-------|-----------|
| 1 | **Problem relevance** | Judge instantly feels the pain & value | /5 | ☐ |
| 2 | **Technical depth** | Real engineering/research, not glue code | /5 | ☐ |
| 3 | **Novelty** | One-sentence wedge no other team has | /5 | ☐ |
| 4 | **Impact & usefulness** | Immediate, undeniable value | /5 | ☐ |
| 5 | **Execution quality** | Robust, clean, tests green, no hacks | /5 | ☐ |
| 6 | **Evidence** | Every claim has `evidence/` number + log | /5 | ☐ |
| 7 | **Demo quality** | Live execution, ≤4:30, sophistication visible | /5 | ☐ |
| 8 | **Documentation** | Grasp in minutes via README → plan → arch | /5 | ☐ |
| 9 | **Scalability** | Path beyond prototype is credible | /5 | ☐ |
| 10| **Judgeability** | Strongest aspects demoable in limited time | /5 | ☐ |

**Weighted priority mirrors tie-break:** 1 ≫ 2 ≫ 3 ≫ 4 — if short on time, fix in that order.

---

## 3. 9 Lenses (one pass per lens — be the critic)

| Lens | Verdict | Top weakness found |
|------|---------|--------------------|
| Technical reviewer | ☐ PASS ☐ FAIL | |
| Research reviewer | ☐ PASS ☐ FAIL | |
| Hackathon judge | ☐ PASS ☐ FAIL | |
| Competitor | ☐ PASS ☐ FAIL | |
| Skeptic | ☐ PASS ☐ FAIL | |
| End user | ☐ PASS ☐ FAIL | |
| Demo judge | ☐ PASS ☐ FAIL | |
| Repro reviewer | ☐ PASS ☐ FAIL | |
| Security / reliability | ☐ PASS ☐ FAIL | |

---

## 4. Triage Queue

| Finding | Lens | Severity | Action |
|---------|------|----------|--------|
| e.g., Advanced delta is only styling | Technical / Skeptic | MUST FIX | Refactor to ≥2-axis delta |
| e.g., Video is 5:40 | Demo | MUST FIX | Cut to 4:30 (see script) |
| e.g., README hot take vague | Skeptic | SHOULD FIX | Sharpen to one line |

Severity: **MUST FIX / SHOULD FIX / NICE TO HAVE / SAFE TO LEAVE**. Fix all MUST + high-impact SHOULD, then re-run `Review → Fix → Test → Reproduce → Review`.

---

## 5. Loop Exit & Final Gate

Loop exits only when **no MUST remains** and weighted score would place in **Top 3 on honest review**.

Final gate questions (answer in `CHANGELOG.md` final entry):

> **If submitted to a highly competitive hackathon today, is there a credible reason judges would place this in Top 3?** — Yes/No + evidence.

> **What specifically prevents it from being #1?** — One weakness; if fixable, fix and re-loop.

---

## 6. Reviewer Output Template

```md
## Review — YYYY-MM-DD HH:MM — <lens or full 9-lens>
Verdict: PASS / FAIL / BLOCKED
Gate: OK / FAIL (<reason>)
Scores: [5,5,4,5,3,5,4,5,4,5] → weighted PASS/FAIL
Must-fix: - <finding> (evidence: file:line)
Should-fix: - <finding>
Evidence: make reproduce <PASS/FAIL> — log: evidence/benchmarks/reproduce.log
Next: fix Must #1 → re-test → re-review
```

---

*Rubric — Aug 28, 2026. Fill one copy per review pass and commit it to `evidence/reviews/`.*
