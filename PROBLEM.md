# Problem Statement — Frontier Engineering Challenge 2026

> **Status:** ⏳ NOT YET RELEASED — Kickoff is Aug 28, 2026 at 15:00 UTC (8:30 PM IST).
> This file is the **single source of truth** for the problem. At kickoff, paste the full PDF text (or converted markdown) here and commit.

---

## How to ingest at T+0

**Option A — you have a PDF:**
```bash
make ingest-problem PROBLEM_PDF=~/Downloads/micro1-frontier-2026.pdf
# → converts via pdftotext (or python pdfminer) into PROBLEM.md + docs/problem-brief.md
```

**Option B — manual:**
1. Open the official problem PDF from the challenge page.
2. Copy **all** text (including constraints, starter repo URL, runtime, dependency limits, API access, testing env, acceptance tests).
3. Replace the placeholder section below.
4. Run `make brief` to auto-generate `docs/problem-brief.md` checklist.

**Option C — URL:**
```bash
make ingest-problem PROBLEM_URL=https://...
```

---

## Placeholder — Replace everything below this line at kickoff

### [PASTE FULL PROBLEM PDF TEXT HERE]

_Example structure to preserve (delete this example and paste real content):_

```
Title:
Context / Real-world scenario:
Constraints:
  - Runtime:
  - Language restrictions:
  - Dependency limits:
  - API / network access:
  - Deterministic judging notes:
Starter repository: <url or "none — greenfield">
Acceptance tests: <path or inline>
Submission format additions (if any beyond the generic package):
```

---

## Distilled Brief (auto-generated)

After ingesting, `docs/problem-brief.md` will contain:

- One-paragraph problem summary
- Constraints table
- Acceptance tests checklist
- Starter repo setup steps
- What "baseline" vs "advanced" means for *this* specific problem
- Risks / hidden dependencies to watch for

Until then, see [docs/problem-brief.md](docs/problem-brief.md) for the pre-kickoff template.

---

## Ingestion Checklist

- [ ] Pasted full PDF text into this file
- [ ] Committed: `git add PROBLEM.md && git commit -m "docs(problem): ingest kickoff PDF"`
- [ ] Ran `make brief` and reviewed `docs/problem-brief.md`
- [ ] Updated `README.md` → Intended User & Value Proposition with real problem context
- [ ] Updated `REPRODUCTION.md` if PDF prescribes a specific runtime/deps
- [ ] Created Day-1 baseline plan in `docs/architecture-decisions.md`

---

*Last updated: pre-kickoff scaffold — Aug 28, 2026*
