# Improvement Changelog

> **Required submission artifact.** Every meaningful iteration gets an entry, connected to the evidence that guided the next decision. Judges read this to see *how you think through code*.

Format per entry: **Iteration → Evidence → Decision → Link → Outcome** (before → after metric).

---

## How to use this file

- Add a new entry **every time** you finish a measurable iteration (not every commit).
- Evidence must point to a file in `evidence/` (benchmark log, test failure, trajectory, profile).
- Outcome must be a number (or "N/A — pre-kickoff scaffold").

---

### #0 — Pre-Kickoff Scaffold — Aug 28, 2026

- **Iteration:** Structured repo scaffold before problem release
- **Evidence:** Challenge brief, FAQs, evaluation tie-break order, submission-package spec (parsed into `docs/evaluation-criteria.md` + `docs/submission-checklist.md`)
- **Decision:** Create `baseline/` vs `advanced/` split, `make reproduce` harness, `evidence/benchmarks/` + `evidence/trajectories/` layout, agent instruction capture, video script template, Docker + Makefile reproducibility
- **Links:** `README.md`, `REPRODUCTION.md`, `docs/problem-brief.md` (template)
- **Outcome:** N/A — scaffold (no real problem yet)
- **Agent:** runner (muse-spark-1.2) + manual orchestration

---

### Template for next entries (copy at kickoff)

```markdown
### #1 — [Short title] — YYYY-MM-DD HH:MM IST

- **Iteration:** What you built/changed in one line
- **Evidence:** What you observed (link file + line): `evidence/benchmarks/results.json:42` — "baseline success 62%"
- **Decision:** What you did next and why (trade-off considered)
- **Links:** PR/commit SHA, trajectory `evidence/trajectories/2026-08-29_<agent>_<task>.json`
- **Outcome:** Before → After — e.g., "success 62% → 84% (+22pp), p95 1.8s → 1.1s, cost $0.42 → $0.31"
- **Kept / Reverted:** Kept / Reverted + reason
```

---

### #1 — [Title] — TBD (kickoff T+0–6h)

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #2 — [Title] — TBD

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #3 — [Title] — TBD

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #4 — [Title] — TBD (most impactful change — star this for video)

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:** ⭐ Highlight in video Ch.3

### #5 — [Title] — TBD (experiment removed — also for video)

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:** 🗑️ Mention in video — what you tried and why you cut it

---

## Changelog Quality Bar (for 9.5/10 reviewer)

- [ ] Every entry has an evidence link that actually exists
- [ ] Every outcome is a number (or explicit "reverted — no gain")
- [ ] At least one entry is marked ⭐ (most impactful) and one 🗑️ (removed experiment) for the video
- [ ] No cosmetic-only entries (advanced delta is real per judging rule)
- [ ] Final entry summarizes failure mode + hot take (mirrors README closing)
