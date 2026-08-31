# Demo Video Script — 5 Minute Max (Target 4:30)

> Requirement: "Begin with the problem and the simple baseline, then walk through one realistic execution from start to finish. Show the final comparison and briefly explain the changelog. Highlight the change that contributed most, and one experiment you removed."
> This version is fully scripted with this project's real numbers, real commands, and real files — nothing in brackets. Read it once cold, then record; adjust phrasing to your own voice, but keep every number as-is (they're pulled live from `evidence/benchmarks/`, not hand-typed).

---

## Chapter 1 — Problem + Simple Baseline (0:00–0:50)

**[On screen: terminal, README.md's "Intended User & Value Proposition" section open]**

> "Our user is solo counsel or an ops lead at a Series A SaaS company, reviewing vendor MSAs — master service agreements. Today they read 80-page contracts under time pressure, hunting for cross-clause traps: a 24-month auto-renewal paired with a 30-day notice window, for example, that quietly locks them in for two more years if they miss a one-month deadline buried three sections away from the renewal clause itself. Missing one of these is expensive and it's easy to miss, because the two clauses that create the trap are never next to each other on the page.
>
> The challenge is a 4-day sprint — build at the frontier of agentic AI, present both a baseline and an advanced solution, back every claim with reproducible evidence, not self-graded scores.
>
> We started with a genuinely simple baseline — single-pass regex, happy-path only, no verification, no evidence citations — in `baseline/src/core.py`. Here it is running against a real contract."

**[Live]**
```
make run-baseline
curl -s -X POST localhost:8000/api/redline -H "Content-Type: application/json" \
  -d '{"contract_id":"cuad_02","contract_text":"'"$(cat shared/fixtures/contracts/cuad_02.txt | head -c 4000)"'"}'
```

> "It finds some clauses by keyword match and stops there — no cross-clause reasoning, no citation a reviewer could actually check, no verification gate. That's the floor we're building above."

---

## Chapter 2 — Realistic Execution, Start to Finish (0:50–2:30)

**[Screen-record live, no slides — this is the actual product]**

> "Here's a real input: `cuad_02`, a real consulting agreement from CUAD, the Contract Understanding Atticus Dataset — 510 contracts hand-labeled by lawyers, the same benchmark we validate against later. This one has exactly the trap I described: a 24-month renewal term against a 30-day notice-to-terminate window.
>
> Now watch the advanced harness handle the same contract, live, streaming its actual stage-by-stage progress — this isn't a canned animation, it's a real SSE stream off the running process."

**[Live]**
```
make run-advanced
curl -N "localhost:8001/api/harness/stream?contract_id=cuad_02"
```

> "Extract stage scans for playbook clause types. Risk stage runs the self-reflective retrieval — it pulls the closest precedent and checks whether the evidence actually covers the trap before proposing anything. Verify stage is the important part: a deterministic dual-threshold gate runs the same check at two thresholds and only proceeds on agreement, plus — when a provider key is configured — a genuine second opinion from an LLM cross-check that can independently flag a finding the deterministic gate passed. Every approved finding carries `{contract_span, page, line, playbook_rule}`, so a human reviewer can jump straight to the exact sentence and verify it themselves — nothing here auto-commits to the contract.
>
> And here's the harness running the same contract through the LangGraph agentic engine instead of the direct pipeline — same verification logic, but now it's a real StateGraph: extract, risk, evidence, verify, and a conditional edge that routes a rejected finding through a genuine revise node — it mechanically shortens an over-long edit or deepens the evidence retrieval, based on *why* verification rejected it — before re-verifying, capped at one retry so it can't loop forever."

**[Live: toggle "Agentic (LangGraph)" in the dashboard's Harness Monitor tab, run cuad_02, show the node trace and the real per-stage latency: extract/risk/verify/route, all real `time.perf_counter()` numbers, not placeholders]**

> "Baseline never catches this trap at all — it has no cross-clause reasoning. Advanced catches it, cites the exact page and line for both clauses, and routes it to human review rather than auto-applying — that's the honest, verification-gated design."

---

## Chapter 3 — Final Comparison, the Money Slide (2:30–3:30)

**[Show `evidence/benchmarks/comparison.md` on screen, scrolled to the primary metric table]**

> "Here's the number that matters most, and it's the one we're proudest of specifically because it's not ours to grade. Every other metric in this repo is checked against gold labels we wrote ourselves — useful for regression testing, but not proof of real generalization. This one is checked against CUAD's own expert legal annotation: 510 real contracts, hand-labeled by lawyers, that we never touched while building the detector.
>
> Baseline: 15.5% recall, 53.7% precision. Advanced: 42.2% recall, 92.7% precision. That's real, externally-validated, roughly a 2.7x recall improvement at almost double the precision — measured with `python scripts/eval_cuad_ground_truth.py`, reproducible from a clean checkout with `make reproduce`.
>
> We also disclose where we're still weak — several individual clause types are still under 30% recall, and we say so directly in the same file, because a number you can't independently check isn't evidence."

**[Show `evidence/benchmarks/results.json` + the dashboard's Metrics tab KPI strip]**

---

## Chapter 4 — Changelog + Most Impactful Change (3:30–4:10)

**[Show `CHANGELOG.md`, scroll to entry #12]**

> "The changelog has 18 entries. The most impactful one is #12: 'Is Trap Recall Fake?' Early on, our headline metric was Trap Recall — 100%, self-graded against gold traps we curated ourselves, using a playbook and fixtures we also wrote. That's not evidence of generalization, no matter how many independently-designed-looking test suites sit on top of it.
>
> So we went looking for real ground truth already sitting unused in the repo — the actual CUAD dataset, cloned at kickoff for reference and never actually used to check anything. We built a real evaluator against it, found the honest number — 37.7% recall at first — then used the *real* failures it surfaced to fix five specific clause types, verified each fix against the actual contract text that exposed it, and re-measured against all 510 contracts each time. Final: 42.2% recall, 92.7% precision, replacing the 100% self-graded number as the reported headline everywhere in this repo — the dashboard, the README, this changelog. That one entry is the difference between a demo that looks good and a result you can actually check."

---

## Chapter 5 — Experiment We Removed (4:10–4:30)

**[Show CHANGELOG entry #5, the 🗑️ marker]**

> "We also built, then deleted, `scripts/ultra_strict_judge.py` and `scripts/judge_committee.py` — about 600 lines of keyword-grep scripts meant to give us a fast, free 'strictness' score to iterate against. What we actually learned: a self-graded heuristic that checks whether a file *contains a word* is trivially gameable — add the word 'async' in a comment, gain the point — and worse, it manufactured false confidence that got published as a claim in the product itself: '100/100, 0 faults.' A real judge has to look at the actual output, not the source code's vocabulary. Not salvageable — we deleted it rather than patch it, and corrected the earlier claim it had produced in the changelog itself, in the same entry where we explain why."

**Outro (4:20–4:30):** "Everything shown here reproduces from a clean checkout with `make reproduce` — baseline, advanced, both eval suites, the dashboard. Thanks for watching."

---

## Recording Checklist

- [ ] 1080p, clear terminal font (14pt+), no secrets on screen — double-check `advanced/.env` is never in frame (it's real API keys, gitignored, must not appear in the recording)
- [ ] Mic check, no background noise
- [ ] Timer visible, hard stop at 4:50
- [ ] Run `make run-baseline` and `make run-advanced` once *before* recording to confirm ports 8000/8001 are free and both boot cleanly, so Chapter 1/2's live commands don't stall on camera
- [ ] Pre-warm the dashboard (`streamlit run app/streamlit_app.py`) so Chapter 2's tab switch and Chapter 3's Metrics tab load instantly, not mid-spinner
- [ ] Export to `evidence/screenshots/demo.mp4` + optional unlisted YouTube
- [ ] Captions / transcript in `evidence/screenshots/transcript.txt` (this file, lightly cleaned of stage directions, is a ready-made first draft)
