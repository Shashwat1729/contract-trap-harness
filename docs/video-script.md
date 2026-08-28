# Demo Video Script — 5 Minute Max (Target 4:30)

> Requirement: "Begin with the problem and the simple baseline, then walk through one realistic execution from start to finish. Show the final comparison and briefly explain the changelog. Highlight the change that contributed most, and one experiment you removed."
> Template timed to 4:30 to leave buffer.

## Chapter 1 — Problem + Simple Baseline (0:00–0:50)

**[On screen: problem one-liner + stakeholder pain]**

> "Our user is [INTENDED USER] who today [BOTTLENECK]. Solving this matters because [VALUE]. The challenge gave us [CONSTRAINTS] and acceptance tests in `PROBLEM.md`."
> "We started with a baseline — single-pass, happy-path only — in `baseline/src/`. Here it is running..."

**[Live: `make run-baseline` + curl + test run]**

## Chapter 2 — Realistic Execution (0:50–2:30)

**[Screen-record one realistic task end-to-end — no slides, live run]**

> "Here's a real input: [EXAMPLE]. Baseline handles it like [DEMO]. Edge case: [EDGE]. Baseline fails gracefully here — that's honest, but not great."
> "Now the same input through advanced: [DEMO advanced]. Notice [WHAT'S BETTER]."

**Commands to show:**
```
make run-baseline & make run-advanced
curl localhost:8000/api/example?q=...
curl localhost:8001/api/example?q=...
```

## Chapter 3 — Final Comparison (2:30–3:30)

**[Show evidence/benchmarks/comparison.md — the money slide]**

> "Numbers in `evidence/benchmarks/comparison.md`: baseline [X% success, Yms p95], advanced [X'% success, Y'ms p95]. That's [Δ]. Cost [Δ]. Measured with `make eval` — here's the log."

**[Show results.json + comparison.md]**

## Chapter 4 — Changelog + Most Impactful Change (3:30–4:10)

**[Show CHANGELOG.md, highlight ⭐ entry]**

> "Our Improvement Changelog has [N] iterations. The biggest win was [#N — TITLE] — evidence [FILE:LINE] showed [OBSERVATION], so we [DECISION], taking success [BEFORE→AFTER]."

## Chapter 5 — Experiment Removed (4:10–4:30)

**[Show 🗑️ entry]**

> "We also tried [EXPERIMENT] but cut it — evidence showed [NO GAIN / ADDED COMPLEXITY], so we reverted. That judgment is also in the changelog."

**Outro (4:30):** "Repo reproducible via `make reproduce` — thanks!"

---

## Recording Checklist

- [ ] 1080p, clear terminal font (14pt+), no secrets on screen
- [ ] Mic check, no background noise
- [ ] Timer visible, hard stop at 4:50
- [ ] Export to `evidence/screenshots/demo.mp4` + optional unlisted YouTube
- [ ] Captions / transcript in `evidence/screenshots/transcript.txt`
