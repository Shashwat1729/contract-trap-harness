# Contributing — Sprint Playbook (Directive-Aligned)

> **Read first:** [`docs/00-EXECUTION-DIRECTIVE.md`](docs/00-EXECUTION-DIRECTIVE.md) — this file is its operational companion.  
> Team size: **1 + agents**. You are the orchestrator; agents are your engineers.

---

## 0. Operating Contract

- `PROBLEM.md` is law after kickoff. If in doubt, re-read it.
- **No code before gates:** Phase 0 + 1 + 2 must be reviewed and committed before implementation (see directive §§2–3).
- Every claim → `evidence/` link. No exceptions.
- `main` is always `make reproduce` green. No broken commits.

---

## 1. Timeline — Aug 28–31 (Asia/Kolkata)

| Window | Phase | Exit gate | Owner |
|--------|-------|-----------|-------|
| **Pre-kickoff → Aug 28 19:30** | Phase 0 scaffolding | `make reproduce` green on stub; this playbook committed | Runner |
| **Aug 28 20:30 → 23:30** | Phase 0 verification + Phase 1 research kick-off | `PROBLEM.md` ingested; `docs/problem-brief.md` signed; 3+ research threads open | Human + Scout |
| **Aug 29 00:00 → 12:00** | Phase 1 deep research | `docs/research/*.md` + `docs/10-RESEARCH-PROTOCOL.md` complete; SOTA + failures + gaps recorded | Scout + Researcher |
| **Aug 29 12:00 → 18:00** | Phase 2 implementation plan v1 → vN | `docs/11-IMPLEMENTATION-PLAN.md` defensible, reviewed against 10 dimensions, ADRs filed | Human + Planner |
| **Aug 29 18:00 → Aug 30 18:00** | Phase 3 baseline → advanced (incremental) | `baseline/` passes acceptance tests; `advanced/` shows ≥2-axis delta in `comparison.md` | Runner + Tester |
| **Aug 30 18:00 → Aug 31 12:00** | Phase 4 dry run + Phase 5 review loops | Hostile-clone `make reproduce` idempotent; 9-lens review with Must-fix queue empty | Reviewer + Human |
| **Aug 31 12:00 → 18:00 UTC** | Phase 6 final gate + submission | `docs/submission-checklist.md` all checked; video ≤4:30; archive uploaded | Human |

**Baseline first, always.** You cannot lose the qualification gate. Advanced is upside.

---

## 2. Daily Loop (repeat per slice)

```bash
# 1. Select smallest valuable slice (from implementation plan)
# 2. Launch agent with exact instructions (versioned file)
make capture-trajectory AGENT=runner TASK=baseline-core
# 3. Agent executes → logs trajectory
# 4. Verify
make test && EVAL_MOCK=1 make eval   # or make eval with live services
# 5. Log evidence
#    evidence/benchmarks/results.json  → numbers
#    CHANGELOG.md                      → Iteration → Evidence → Decision → Outcome
# 6. Commit atomic
git add baseline/src evidence/benchmarks/results.json CHANGELOG.md
git commit -m "feat(baseline): <slice> — success 62%→71%"
```

**Discipline:**
- One slice at a time. No blind parallel big-bangs.
- Tests alongside code, not after.
- Decision freshly documented (`ARCHITECTURE.md` / ADR) before next slice.
- Any manual step found → turn it into a script before committing.

---

## 3. Branching & Version Control

- `main` — always green. Direct commits allowed for docs/small slices; feature branches optional.
- `feat/baseline-*`, `feat/advanced-*`, `feat/research-*` — short-lived if you branch; merge with `--no-ff`.
- **Never:** `git push --force`, `git reset --hard`, `git branch -D` on shared history. History is trajectory evidence.
- Commit messages (conventional):
  ```
  feat(baseline): add happy-path handler for X
  feat(advanced): retry with verification — success 71%→84%
  eval(harness): wire acceptance tests from PDF
  research(topic): SOTA on Y — gap found
  review(docs): 9-lens review — fix P0: <issue>
  docs(trajectory): capture Codex session for baseline
  ```

---

## 4. Agent Orchestration

| Agent | When | Instruction file | Output |
|-------|------|------------------|--------|
| **Scout** (`hy3-free`) | Exploration, codebase mapping | `.agent/instructions/scout.md` | File list + relevance |
| **Runner** (`muse-spark-1.2`) | Primary build | `.agent/instructions/runner.md` | Code + tests |
| **Reviewer** (`nemotron-3-ultra`) | After risky change, before merge | `.agent/instructions/reviewer.md` | PASS/FAIL with evidence |
| **Tester** (`hy3-free`) | Test generation, coverage | `.agent/instructions/tester.md` | Tests + reports |
| **Human** | Gates, approvals, directive audits | — | `[HUMAN CHECKPOINT: ...]` in trajectory |

All agent sessions are captured: `scripts/capture_trajectory.sh` → `evidence/trajectories/YYYY-MM-DD_HHMM_<agent>_<task>.json`. Instructions are code — versioned in `.agent/instructions/`.

---

## 5. Rule Book Compliance (non-negotiable)

- ✅ Every tool/component used per its licence (noted in `ARCHITECTURE.md`).
- ✅ Consequential actions (network writes, deploys, payments, deletions) sandboxed/simulated + **human approval** gated. Mark `[HUMAN CHECKPOINT]` in trajectory.
- ✅ Qualified human reviewer in any high-impact path.
- ✅ Legal/ethical use case, responsible data (public/synthetic/approved anonymous only).
- ✅ Credentials never in git (`.env` only, `.gitignore` enforced).
- ✅ Every claim → `evidence/` link (enforced by reviewer rubric).
- 🚫 No retroactive trajectory edits.

---

## 6. Review Gates (when to call Reviewer)

Call Reviewer **before** marking any of these done:
- `docs/11-IMPLEMENTATION-PLAN.md` v1 and every major revision
- `baseline/` passing acceptance tests
- `advanced/` claiming a delta
- `ARCHITECTURE.md` / ADR affecting reversibility
- Final gate (Phase 6)

Reviewer output must be `PASS / FAIL / BLOCKED` with evidence line references. `FAIL` → Must-fix queue, no progress until cleared.

---

## 7. Reproduction & Pre-Submit

**Single judge command:**
```bash
git clone <url> && cd micro1-front && cp .env.example .env && make reproduce
```

**Pre-submit (full audit):**
```bash
make pre-submit
# → secret scan + reproduce + comparison delta + trajectory coverage + video length + README 10-dimension check
```

Manual final checklist: [`docs/submission-checklist.md`](docs/submission-checklist.md) + [`docs/20-REVIEW-RUBRIC.md`](docs/20-REVIEW-RUBRIC.md)

---

## 8. If You Have 30 Minutes Left

In priority order (tie-break from brief):
1. Make `make reproduce` green (qualification gate).
2. Make `advanced` vs `baseline` delta undeniable (≥2 axes in `comparison.md`).
3. Make video ≤4:30 live execution (judgeability).
4. Polish trajectories.

Anything else is lower than these.

---

*This playbook is binding. Deviations must be logged as an ADR with rationale.*
