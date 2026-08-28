# Improvement Changelog

> **Required submission artifact — and the heart of the Directive.** Every meaningful iteration gets an entry, connected to the evidence that guided the next decision. Judges read this to see *how you think through code*.  
> Execution is governed by [`docs/00-EXECUTION-DIRECTIVE.md`](docs/00-EXECUTION-DIRECTIVE.md) (6 phases) and judged by [`docs/20-REVIEW-RUBRIC.md`](docs/20-REVIEW-RUBRIC.md) (10 dimensions, 9 lenses).

**Format per entry:** Iteration → Evidence → Decision → Link → Outcome (before → after metric). No cosmetic-only entries.

---

## Phase Gates

| Phase | Gate artifact | Status |
|-------|---------------|--------|
| **0 Scaffolding** | `docs/problem-brief.md` signed, `ARCHITECTURE.md` §7 checked, `make reproduce` on stub | ✅ Done 2026-08-28 |
| **1 Research** | `docs/research/*.md` + `docs/10-RESEARCH-PROTOCOL.md` synthesis | ☐ Kickoff |
| **2 Plan** | `docs/11-IMPLEMENTATION-PLAN.md` reviewed & approved (Reviewer PASS) | ☐ |
| **3 Implementation** | `baseline/` green → `advanced/` ≥2-axis delta in `comparison.md` | ☐ |
| **4 Dry run** | Hostile-clone `make reproduce` idempotent green | ☐ |
| **5 Review loops** | `docs/20-REVIEW-RUBRIC.md` — no MUST FIX remains | ☐ |
| **6 Final gate** | Top 3 credible + blocker for #1 named below | ☐ |

---

## How to use this file

- Add a new entry **every time** you finish a measurable iteration (not every commit).
- Evidence must point to a file in `evidence/` (benchmark log, test failure, trajectory, profile).
- Outcome must be a number (or explicit "N/A — gated" / "reverted — no gain").
- Mark ⭐ the most impactful change and 🗑️ one removed experiment — both are required in the video (`docs/video-script.md` Ch.4–5).

---

### #0 — Pre-Kickoff Scaffold — Aug 28, 2026 (Phase 0)

- **Iteration:** Structured repo scaffold before problem release — baseline/advanced split, Docker + Makefile, eval harness, trajectory capture, 6-phase directive.
- **Evidence:** Challenge brief, FAQs, tie-break order, submission-package spec → `docs/evaluation-criteria.md` + `docs/submission-checklist.md`
- **Decision:** Build reproducibility-first scaffold (independent services, `shared/` only where justified, `EVAL_MOCK=1` offline path, 4:30 video template). Encode competition standard (10 dimensions) in `00-EXECUTION-DIRECTIVE.md`.
- **Links:** Commit `e63fd98` — `README.md`, `REPRODUCTION.md`, `docs/00-EXECUTION-DIRECTIVE.md`, `docs/10-RESEARCH-PROTOCOL.md`, `docs/11-IMPLEMENTATION-PLAN-TEMPLATE.md`, `docs/20-REVIEW-RUBRIC.md`
- **Outcome:** N/A — scaffold (no real problem yet)
- **Agent:** runner (muse-spark-1.2) + manual orchestration
- **Gate:** Phase 0 scaffold ✅

---

### #0.1 — Directive & Documentation Hardening — Aug 28, 2026 (Phase 0)

- **Iteration:** Rewrite raw execution directive into `docs/00-EXECUTION-DIRECTIVE.md` (6 phases, 10 dimensions, anti-patterns, traceability); replace `CONTRIBUTING.md` with rigorous sprint playbook; create `10-RESEARCH-PROTOCOL.md`, `11-IMPLEMENTATION-PLAN-TEMPLATE.md`, `20-REVIEW-RUBRIC.md`; upgrade `README`, `ARCHITECTURE`, `evaluation-criteria`, `problem-brief` to 1st-place bar.
- **Evidence:** User directive (Aug 28) + audit of prior docs (see commit diff) — prior docs lacked research depth, review loops, 10-dimension mapping, and hostile-clone dry run protocol.
- **Decision:** Elevate docs from "scaffold" to "competition operating system" — every future decision is judged by Directive §3 (10 dimensions) and must survive 9-lens review (`20-REVIEW-RUBRIC.md`). Research depth (≥12 sources, ≥3 failures) is a gate before planning.
- **Links:** This commit — all docs/* diffs
- **Outcome:** Docs now defensible for elite review; `make reproduce` still green (6+6+1 tests, eval mock 80%→100%)
- **Agent:** runner
- **Gate:** Phase 0 docs hardened ✅

---

### Template for next entries (copy at kickoff)

```markdown
### #1 — [Short title] — YYYY-MM-DD HH:MM IST — Phase X

- **Iteration:** What you built/changed in one line
- **Evidence:** What you observed (link file + line): `evidence/benchmarks/results.json:42` — "baseline success 62%"
- **Decision:** What you did next and why (trade-off considered, alternative rejected)
- **Links:** PR/commit SHA, trajectory `evidence/trajectories/2026-08-29_<agent>_<task>.json`, plan ref `docs/11-IMPLEMENTATION-PLAN.md` §__
- **Outcome:** Before → After — e.g., "success 62% → 84% (+22pp), p95 1.8s → 1.1s, cost $0.42 → $0.31"
- **Kept / Reverted:** Kept / Reverted + reason
- **Research tie:** `docs/research/X.md` — gap/limitation that motivated this
```

---

### #1 — [Title] — TBD (kickoff T+0–6h) — Phase 1/2

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #2 — [Title] — TBD — Phase 3

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #3 — [Title] — TBD — Phase 3

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:**

### #4 — [Title] — TBD — Phase 3 (most impactful — star this for video)

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:** ⭐ Highlight in video Ch.4

### #5 — [Title] — TBD — Phase 3/5 (experiment removed — for video)

- **Iteration:**
- **Evidence:**
- **Decision:**
- **Links:**
- **Outcome:** 🗑️ Mention in video — what you tried, evidence of no gain, why you cut it

---

### Final Gate — TBD (Phase 6) — fill before submission

> **If submitted to a highly competitive hackathon today, is there a credible reason judges would place this in Top 3?** — Yes/No + evidence: __

> **What specifically prevents it from being #1?** — One weakness: __ (if fixable, fix and re-loop per Directive §5).

---

## Changelog Quality Bar (for 9.5/10 reviewer — Directive Phase 5)

- [ ] Every entry has an evidence link that actually exists
- [ ] Every outcome is a number (or explicit "reverted — no gain")
- [ ] At least one entry is marked ⭐ (most impactful) and one 🗑️ (removed experiment) for the video
- [ ] No cosmetic-only entries (advanced delta is real per judging rule — ≥2 axes)
- [ ] Phase gates table above is maintained; no phase marked ✅ without its artifact committed
- [ ] Final gate answers are present and honest (Directive §6)
