# Contributing — Sprint Workflow

> You are solo (team size = 1) but your **agents are your team**. This doc is your Day 1–3 playbook to move fastest.

---

## 1. Sprint Plan (Aug 28–31)

| Day | Focus | Exit criteria |
|-----|-------|---------------|
| **Day 0 (tonight)** | Scaffold ✅ + rehearse repro + draft agent prompts | `make reproduce` green on scaffold |
| **Day 1 (Aug 29)** | Ingest PDF → baseline green | `baseline/tests` green, `make run-baseline` passes acceptance tests |
| **Day 2 (Aug 30)** | Advanced delta + eval harness | `evidence/benchmarks/comparison.md` shows measured win on ≥2 axes |
| **Day 3 (Aug 31)** | Polish, video, trajectories, submission zip | `docs/submission-checklist.md` all checked, `make reproduce` green offline |

**Baseline first, always.** You cannot lose the qualification gate. Advanced is upside.

---

## 2. Fast Workflow (repeat loop)

```bash
# 1. Pick next iteration (smallest valuable slice)
# 2. Run agent with exact prompt (logged to .agent/instructions/)
make agent-run TASK="implement <slice> in baseline/src"
# 3. Verify
make test && make eval
# 4. Log evidence
#    → evidence/benchmarks/results.json
#    → CHANGELOG.md new entry with evidence link
# 5. Commit small
git add baseline/src evidence/benchmarks/results.json CHANGELOG.md
git commit -m "feat(baseline): <slice> — success 62%→71%"
```

---

## 3. Branching

- `main` — always green (`make reproduce` passes)
- `feat/baseline-*` / `feat/advanced-*` — short-lived, merge via `git merge --no-ff`
- Never force-push. History is part of trajectory evidence.

---

## 4. Agent Use Rules (per Rule Book)

- ✅ Use every tool according to its licence
- ✅ Keep consequential actions sandboxed — require human approval before real side-effects
- ✅ Treat agent instructions as code — commit them in `.agent/instructions/`
- ✅ Disclose all agents in `README.md` + `docs/agent-instructions.md`
- 🚫 Don't paste secrets (keys in `.env` only, never committed)
- 🚫 Don't claim results without linking `evidence/` (every claim → evidence)

---

## 5. Commit Convention

```
type(scope): description

Types: feat, fix, docs, test, chore, eval, trajectory, video
Scopes: baseline, advanced, shared, harness, repro, docs

Examples:
  feat(baseline): add happy-path handler for X
  feat(advanced): retry with verification — success 71%→84%
  eval(harness): wire acceptance tests from PDF
  docs(trajectory): capture Codex session for baseline
```

---

## 6. Human Checkpoints (required by Rule Book)

At least these need **your explicit approval** before the agent executes:

- Any network write / deploy / payment / data deletion
- Pushing a tag / publishing a package
- Modifying `PROBLEM.md` after kickoff ingest

Mark checkpoints in trajectories: `[HUMAN CHECKPOINT: approved ...]`.

---

## 7. Pre-Submit Checklist (run before zipping)

```bash
make pre-submit
# → checks:
#   - no secrets in git (gitleaks pattern)
#   - make reproduce green
#   - evidence/benchmarks/comparison.md exists and shows delta
#   - trajectories cover every agent in docs/agent-instructions.md
#   - video ≤ 5 min (docs/video-script.md timed)
#   - README has user/bottleneck/value/changelog/failure/hot-take
```
