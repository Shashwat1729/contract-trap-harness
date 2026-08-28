# Problem Brief — Distilled (T+0 Template)

> Pre-kickoff template. At T+0, ingest `PROBLEM.md` then distill here via `make brief`.  
> This file is the **one-page handshake** between the PDF and the implementation plan. Keep it to one page — judges and agents both read it.

## Source

- **PROBLEM.md ref:** _(section + page, or commit SHA after ingest)_
- **Ingested:** 2026-08-__ __:__ IST by ___
- **Research base:** `docs/research/00-synthesis.md` (after Phase 1)

---

## 1. One-Paragraph Summary

_Paste one paragraph: what is being built, for whom, under what constraints, judged how. The sentence a judge reads before anything else. No jargon without definition._

---

## 2. Constraints (verbatim from PDF + impact)

| Constraint | Value (verbatim or N/A) | Impact on design |
|------------|------------------------|------------------|
| Runtime | _e.g., Python 3.11 only_ |  |
| Starter repo | _url or greenfield_ |  |
| Dependency limits | _e.g., no GPL, max 20 deps_ |  |
| Network / API access | _allowed / sandboxed / offline_ |  |
| Data allowed | _public / synthetic / approved anon_ |  |
| Deterministic judging | _how evaluation is run_ |  |
| Language | _Python/TS/Java/C++/Go/Rust — which is prescribed_ |  |
| Resource caps | _e.g., time, memory, cost_ |  |

---

## 3. Acceptance Tests (copy verbatim — do not paraphrase)

- [ ] _Test 1 — paste exact wording from PDF_
- [ ] _Test 2_
- [ ] _Edge case 1_
- [ ] _Hidden dependency note (if any)_
- [ ] _Scoring / metric as stated (success rate, latency, cost, coverage, etc.)_

> Each acceptance test becomes a **contract test** in `baseline/tests/integration/` + `tests/e2e/` on Day 1. No contract test → no claim.

---

## 4. What Baseline vs. Advanced Means for *This* Problem

| Baseline | Advanced (≥2 axes, non-cosmetic) |
|----------|----------------------------------|
| _e.g., Single-pass agent, happy-path only, passes X% of acceptance tests_ | _e.g., + retry with calibrated verifier (reliability) + cache (efficiency) → +22pp success, −40% p95, with `comparison.md` proof_ |

**Forbidden per brief:** Cosmetic-only variation (same logic, different styling) = disqualification risk.

---

## 5. Hidden Risks & Day 1 Spikes (pre-mortem)

- _e.g., Rate-limited API — spike: contract test + fallback stub by T+6h_
- _e.g., Ambiguous spec on edge case — decision + ADR + documented assumption_
- _e.g., Missing fixture — synthetic generator + seed_

---

## 6. Starter Repo Delta (if provided)

See `ARCHITECTURE.md` §8 — table: `File from starter | Kept | Modified | Added | Reason`. Required by Rule Book: "Make it clear what existed before the competition and what you added."

---

## 7. Open Questions → Plan for Directive Phase 1

_List what research must answer before the implementation plan is drafted (track A–E)._

- _Q1 → Track _ — _
- _Q2 → Track _ — _

---

*Template — Aug 28, 2026. After ingesting, commit: `docs: ingest problem brief for <title>`.*
