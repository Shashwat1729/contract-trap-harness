# Research Protocol — Before You Code

> Mandatory Phase 1. No implementation plan passes review without this.  
> Goal: Avoid building the obvious solution that 80% of teams will build — find the gap.

---

## 1. Research Tracks (run in parallel)

### Track A — Papers & Technical Publications
- **Where:** arXiv, Semantic Scholar, ACL/NeurIPS/ICLR/ICSE proceedings, company research blogs.
- **What:** SOTA techniques, model architectures, theoretical limits, benchmark suites.
- **Output:** `docs/research/A-papers-<topic>.md` — 3–5 papers, each with *approach / result / limitation / relevance to our problem*.

### Track B — Open-Source Reality
- **Where:** GitHub (sort by stars, read issues/PRs), Hugging Face, Awesome lists, Stack Overflow.
- **What:** Implementation patterns, actual failure modes, scaling cliffs, dependency traps, license constraints.
- **Output:** `docs/research/B-oss-<topic>.md` — 3–5 repos, each with *what works / what breaks / what we'd steal / what we'd avoid*.

### Track C — Engineering Writing & Case Studies
- **Where:** Engineering blogs (Vercel, Cloudflare, Anthropic, etc.), benchmark reports, post-mortems, case studies.
- **What:** Cost/latency/accuracy trade-offs at scale, operational wisdom, evaluation tricks.
- **Output:** `docs/research/C-eng-<topic>.md` — distilled numbers, not opinions.

### Track D — Community Signal
- **Where:** Reddit (r/MachineLearning, r/programming, domain subs), Hacker News, Discord, X expert threads.
- **What:** Practitioner pain, hype gaps, tooling frustrations, edge cases users actually hit.
- **Output:** `docs/research/D-community-<topic>.md` — quotes + link, with *signal vs. noise* judgment.

### Track E — Competitive Landscape
- **Where:** Prior hackathon winners, Product Hunt, competitor teardowns, judging rubrics.
- **What:** What "good" looks like, what judges have rewarded before, where differentiation room exists.
- **Output:** `docs/research/E-competitive.md` — *obvious solution vs. our wedge*.

---

## 2. For Each Source, Record

| Field | Example |
|-------|---------|
| **Source** | `arXiv:2407.12345 — Agentic Workflow Evaluation` |
| **Approach** | Multi-agent debate with verifier |
| **Result** | +12% accuracy, 2.3× cost |
| **Limitation / failure** | Collapses on ambiguous tool output; no calibration |
| **Evaluation method** | 500-task SWE-bench subset, p95 latency |
| **Opportunity for us** | We can win on *calibrated verification* at lower cost via caching + smaller verifier |

> Failed approaches are **as valuable** as successful ones — they tell you where not to waste 6 hours.

---

## 3. Synthesis — From Notes to Gap

After tracks, synthesize in `docs/10-RESEARCH-PROTOCOL.md` §Synthesis (or `docs/research/00-synthesis.md`):

1. **SOTA landscape in 5 bullets** — what's genuinely best today.
2. **3 hard limitations** — where SOTA fails (these are our wedge).
3. **Obvious hackathon solution** — the thing most teams will build (and why it won't win).
4. **Our differentiation thesis** — one sentence: *"We are the only team that does X, proven by Y."*
5. **Open questions** — what we still don't know and will spike in Phase 2.

---

## 4. Quality Bar

- [ ] ≥12 distinct sources across ≥4 tracks (not just Google top-5).
- [ ] ≥3 failed/limitation notes (not just success stories).
- [ ] At least one benchmark number per track (not vague "better").
- [ ] Differentiation thesis is falsifiable and ties to a measurable delta in `comparison.md`.
- [ ] All notes committed before implementation plan review is requested.

---

## 5. Anti-Patterns

- Surface-level "Top 5 approaches" blog summary — **reject**.
- Copy-pasting abstract without reading method/limitations — **reject**.
- No community / failure notes — **incomplete**.
- Research filed after coding started — **gate violation**.

---

## 6. Templates

Create per-thread notes as:
```
docs/research/
├── 00-synthesis.md
├── A-papers-agent-verification.md
├── B-oss-langgraph-workflows.md
├── C-eng-eval-at-scale.md
├── D-community-pain-points.md
└── E-competitive.md
```

Each file starts with:
```md
# Research: <Topic> — <Track>
Date: 2026-08-XX
Sources: [links]
Summary: 3-bullet TL;DR
Findings: (table above)
Implication for us: 1 paragraph
```
