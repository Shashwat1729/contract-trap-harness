# Contract Trap Harness — Source Document for AI-Generated Video/Audio Overview

> **Purpose of this file:** this is a self-contained source document, written to be uploaded
> directly into NotebookLM (or a similar tool) to generate an AI video or audio overview for
> a hackathon presentation. It contains the full story of the project — problem, design,
> evidence, honest limitations — with real numbers and tables, so a generated narration has
> everything it needs without guessing or inventing facts. Every number in this document is
> sourced from a real, reproducible file in this repository (cited inline), not invented for
> the presentation. If you are a human reading this instead of an AI: this is also a fair
> single-document summary of the whole project.

---

## 1. The 30-second pitch

**A solo lawyer or ops lead at a small SaaS company has to review an 80-page vendor contract
under time pressure, looking for a handful of specific "traps" — clauses that quietly lock
the company into bad terms. This project builds an AI system that reads the contract, finds
those traps, and — critically — only tells the reviewer about a finding it can actually prove
with a verbatim quote from the contract. It never invents a citation. It never auto-edits the
contract. Every claim it makes is checked twice before it's shown to a human, and if it can't
find defensible evidence, it says nothing rather than guessing.**

The system was built for a 4-day hackathon ("Frontier Engineering Challenge 2026," organized
by micro1) whose explicit theme was: *"Build at the frontier of agentic AI — where convincing
is not enough."* The rules require every entry to submit both a **baseline** (a deliberately
simple, honest solution) and an **advanced** solution, and to prove the advanced one is a real
improvement with reproducible evidence — not polish, not a nicer UI, not a self-graded score.

---

## 2. The problem, in concrete terms

**Who:** solo counsel or an ops lead at a Series A SaaS company, reviewing vendor Master
Service Agreements (MSAs).

**What they're hunting for:** cross-clause "traps" — pairs or combinations of clauses that are
individually unremarkable but dangerous together. The canonical example used throughout this
project: a contract auto-renews every **24 months**, but the window to give notice and opt out
of that renewal is only **30 days**. Miss that 30-day window — easy to do, because the renewal
clause and the notice clause are usually in different sections, pages apart — and the company
is locked in for two more years.

**Why it's hard:** an 80-page contract, read under deadline pressure, by someone who is not
necessarily a contracts specialist. The dangerous combinations are never adjacent on the page.

**What "solving" it means for this project:** build a system that (a) finds these clauses,
(b) checks them against a playbook of what "good" and "bad" language looks like, (c) never
tells the reviewer something is a problem unless it can point to the exact sentence and page,
and (d) never silently rewrites the contract — every finding routes to a human for a decision.

---

## 3. Two solutions, on purpose: Baseline vs Advanced

The hackathon rules require both. This project treats that requirement as a genuine design
exercise, not a formality.

| | **Baseline** | **Advanced** |
|---|---|---|
| Approach | Single-pass regex keyword matching | Multi-stage verification-gated pipeline |
| Verification | None — whatever regex finds is reported | Two independent gates before anything is shown |
| Evidence | No citation guarantee | Every finding carries `{contract_span, page, line, playbook_rule}` |
| Cross-clause reasoning | None | Yes — explicitly checks combinations like the renewal/notice trap |
| Extraction layers | Regex only | Regex + optional real-embedding semantic layer + optional BM25 lexical layer + optional LLM-as-generator |
| Human review | None | Explicit routing; can genuinely pause execution for a human decision (real LangGraph `interrupt()`) |
| Auto-edits the contract? | No | No — by design, in both |

Baseline exists so the advanced system's improvement can be measured against something
real and honest, not a strawman. It is a legitimate, working, if limited, solution on its own.

---

## 4. How the Advanced pipeline actually works (the "harness")

The system is called the **Contract Trap Harness**. A contract goes through five real stages:

1. **Extract** — find candidate clauses in the contract text. The default layer is regex
   pattern matching against 12 distinct clause types (Renewal Term, Notice Period, Cap on
   Liability, Governing Law, Non-Compete, IP Ownership Assignment, etc.). Two additional,
   independently-toggleable layers can extend this: a real hosted-embedding **semantic**
   layer (catches clauses regex's fixed patterns miss because of unusual phrasing) and a
   **BM25** classical lexical-scoring layer (catches close wording matches at zero cost).
2. **Risk assessment** — a 12-rule playbook checks each found clause against what makes it
   risky (e.g., "Renewal Term" is fine at 12 months, but flagged if the contract auto-renews
   for longer than that). This also runs a "self-reflective" retrieval step that pulls the
   closest real-world precedent language for that clause type and checks whether the evidence
   genuinely supports the finding before proposing it.
3. **Evidence verification (the core safety mechanism)** — every proposed finding must pass a
   **deterministic dual-threshold gate**: the same span-in-contract check run at two different
   strictness thresholds in parallel, and only findings where both thresholds agree get
   through cleanly. When a real LLM provider key is available, a genuine second-opinion LLM
   call can independently downgrade a finding the deterministic gate approved — a real second
   check, not a rubber stamp, and it can only make the system MORE conservative, never less.
4. **Human review routing** — every approved finding is packaged with its exact contract
   citation and routed for human review. Nothing is auto-applied to the contract. When the
   system is run through its "agentic" LangGraph engine with human-in-the-loop enabled, a
   rejected finding can genuinely **pause the entire program execution** (using LangGraph's
   real `interrupt()` primitive, not a UI simulation) until a human explicitly overrides or
   confirms the decision — fully auditable, logged, and resumable.
5. **Reporting** — approved findings can be turned into an actual redlined Word document
   (`.docx`) with tracked changes, or streamed live to a dashboard.

### The anti-hallucination design, explained simply

The single most important design decision in this project: **a finding is worthless if the
citation it points to isn't real.** So every finding — no matter which layer proposed it
(regex, semantic embeddings, BM25, or the LLM-as-generator layer described below) — must pass
an exact-substring check against the real contract text before it can be shown to a human.
Text that doesn't verify is discarded, not "shown with lower confidence." This is why the
system's precision is high even though its recall (see the numbers below) is not perfect: it
is deliberately built to say nothing rather than guess.

---

## 5. Two agentic engines, run side by side

The harness can run in two modes, chosen at request time — a direct "just call the functions
in order" pipeline, or a real **LangGraph** state-machine ("agentic") engine with the identical
verification logic wired as explicit graph nodes: `extract → risk → evidence → verify →
revise → human_review`. Both modes are kept in exact parity (same flags, same thresholds,
same outputs) so a judge can compare them directly.

The agentic engine implements two named, citable agentic design patterns, not "agentic" as a
buzzword:

- **Reflection** (Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement
  Learning," 2023) — a rejected finding is mechanically revised based on the SPECIFIC reason
  it was rejected (e.g., an over-long proposed edit gets shortened to the surgical minimum; a
  missing precedent triggers a deeper retrieval pass), then re-enters verification. Capped at
  one retry so it cannot loop forever.
- **Human-in-the-loop** — a real pause-and-resume cycle via LangGraph's `interrupt()` /
  `Command(resume=...)` primitives. The graph's execution state is checkpointed (in-memory by
  default, or to a real SQLite file for durability across restarts) and only continues once a
  human supplies an explicit decision.

---

## 6. The headline result — real, external, independently-labeled evidence

**This is the number the project is proudest of, specifically because the labels are not its
own.** Every other metric in this project is checked against gold labels the team wrote itself
— useful for catching regressions, but not proof the system generalizes. This one number is
checked against **CUAD** (the Contract Understanding Atticus Dataset, Hendrycks/Burns/Chen/Ball,
NeurIPS 2021) — 510 real contracts, hand-labeled by lawyers, that were never touched while
building the detection logic's regex patterns... with one caveat stated plainly: the patterns
*were* iteratively improved by reading real failures off this same 510-contract set (a
standard "read the errors, fix the errors" loop), so this is best read as "best iteratively-
achieved performance on CUAD," not a result guaranteed to reproduce cold on a disjoint sample.

| System | Recall | Precision |
|---|---|---|
| Baseline | 15.5% | 53.7% |
| **Advanced** | **42.2%** | **92.7%** |

That's roughly a **2.7x improvement in recall, at nearly double the precision** — measured on
510 real contracts, reproducible from a clean checkout with `python
scripts/eval_cuad_ground_truth.py` or `make eval-cuad-ground-truth`.

### Per-rule breakdown (all 11 measurable rules, 510 real contracts)

| Rule | Advanced Recall | Advanced Precision | Baseline Recall | Baseline Precision | Real contracts with this clause (n) |
|---|---|---|---|---|---|
| Renewal Term | 61.9% | 90.8% | 0.0% | n/a | 176 |
| Notice Period to Terminate Renewal | 19.8% | 95.7% | 45.0% | 26.9% | 111 |
| Termination for Convenience | 13.7% | 92.6% | 7.7% | 87.5% | 183 |
| Cap / Uncapped Liability | 51.6% | 94.7% | 85.5% | 64.6% | 275 |
| Audit Rights | 26.6% | 95.0% | 13.1% | 65.1% | 214 |
| Governing Law | 74.1% | 99.1% | 0.0% | n/a | 437 |
| License Grant | 42.4% | 98.2% | 0.0% | n/a | 255 |
| Non-Compete | 31.9% | 69.1% | 0.0% | n/a | 119 |
| Non-Disparagement | 23.7% | 81.8% | 0.0% | n/a | 38 |
| IP Ownership Assignment | 35.5% | 86.3% | 0.0% | n/a | 124 |
| Post-Termination Services | 8.2% | 51.7% | 0.0% | n/a | 182 |

**Why does baseline "win" on 2 of the 11 rules (Notice Period, Cap on Liability)?** This is
disclosed and explained, not hidden: baseline's pattern for these two rules is deliberately
broad and unanchored (e.g., "the word notice, near a day-count, anywhere within 150
characters") — it catches more raw instances but also many false positives (26.9% precision,
meaning roughly 3 of every 4 flags are wrong). Advanced's pattern is anchored to the actual
clause header language, trading some recall for much higher precision — a deliberate, disclosed
design choice consistent with the project's stated identity: **"high precision, conservative
recall" over "flag everything and let the human sort it out."**

### How this compares to published, independent results on the same dataset

Not a like-for-like comparison (different metric — presence detection is a looser task than
exact span-match), but included as an honest neighborhood check:

| Method | Metric | Result | Source |
|---|---|---|---|
| DeBERTa-xlarge, fully supervised (fine-tuned on CUAD) | AUPR / precision @ 80% recall | 47.8% / 44.0% | CUAD paper (arxiv.org/abs/2103.06268) |
| BERT-base, fully supervised | precision @ 80% recall | 8.2% | same paper |
| GPT-4.1, zero-shot | span-match F1 | 0.641 | ContractEval, 2025 (arxiv.org/abs/2508.03080) |
| DeepSeek-R1-Distill-7B, zero-shot | span-match F1 | 0.071 | same paper |
| **This system (Advanced), zero training, rule-based** | presence recall / precision | **42.2% / 92.7%** | this repo |

**Honest read:** a fully-supervised, fine-tuned transformer tops out around 44-48% on the
harder task; a frontier zero-shot LLM lands around 0.64 F1. This system's zero-training,
rule-based number sits in a credible neighborhood of both — not a claim of beating either.

### Secondary metrics (self-graded regression suite, useful but not independent proof)

| Metric | Baseline | Advanced | Change |
|---|---|---|---|
| Trap Recall (curated gold traps) | 56% | 100% | +44pp |
| Evidence-supported edit rate | 21.4% | 83.7% | +62.2pp |
| Unsupported edit rate | 78.6% | 16.3% | -62.2pp |
| Over-redlining avg / contract | 2.33 | 1.63 | -0.70 |
| Est. human review time / contract | 5.1 min | 3.4 min | **-1.7 min (-33%)** |
| p95 latency | 1.0ms | 59.8ms | +58.7ms (still near-instant) |

The review-time reduction is a disclosed *formula* (not a live user study): 120 seconds of
skim time, plus 45 seconds per supported finding, plus 90 seconds per unsupported one — a
transparent estimate, not a measurement dressed up as one.

### An honest, live, real-API data point (not mocked)

A real, live zero-shot comparison against `gemini-2.5-flash` — asked cold, with no
CUAD-specific prompt tuning — got through 1 of 10 planned real contracts before hitting the
provider's free-tier daily quota cap. That one real data point: 33.3% recall, 100.0%
precision. **n=1 is explicitly too small to draw a conclusion from** — it's disclosed as a
genuine, non-fabricated result, not a settled comparison.

---

## 7. The optional, opt-in extraction layers — and why they're OFF by default

Three additional capabilities exist beyond the certified regex-only default, all disabled
unless explicitly turned on, because each one trades away some precision for more recall —
a deliberate choice that should be made knowingly, not silently baked into the default numbers
everyone sees first.

| Layer | Mechanism | Cost | Validation | Real effect (when enabled) |
|---|---|---|---|---|
| Semantic extraction | Real hosted embeddings (`gemini-embedding-001`) scored against official CUAD category descriptions | Paid API call per document | n=7 real contracts (quota-limited) | Recall 45.5% → 52.3% (+6.8pp), precision 100% → 74.2% on that small sample |
| BM25 lexical hybrid | Classical Okapi BM25 (`rank_bm25`) scored against the same category descriptions | **$0**, no network | Full 510-contract set (fully validated) | Recall 42.2% → 46.1% (+3.9pp), precision 92.7% → 88.1% (-4.6pp) |
| LLM-as-generator | Asks an LLM to locate a verbatim excerpt for playbook clause types with ZERO hits from every other layer | Paid API call, capped at 6 calls/document | 1 real successful live call (existence proof, not a full sweep) | Closes the "every LLM call only ever filters, never proposes" gap identified by an internal strict-review audit |

The **LLM-as-generator** layer deserves a specific mention because of what makes it safe: it
is only ever allowed to *locate* text, never to *describe* or *invent* it. Any span it returns
is checked against the real contract text with an exact-substring match before it can become a
candidate — and even after that, it still has to pass the exact same risk-assessment and
dual-verification gates as everything else. Three independent checks stand between "the LLM
said this exists" and "the reviewer sees this as a finding."

---

## 8. The development story — real bugs found, real fixes made

This project's changelog contains 22 real, evidence-linked entries (`CHANGELOG.md`). A few are
worth telling as the narrative arc of the project, because they show the actual discipline
behind the numbers above, not just the numbers.

### The most impactful single change: "Is Trap Recall Fake?"

Early in the build, the headline metric was **100% Trap Recall** — but it was measured against
gold-standard traps the team wrote itself, using a playbook it also wrote. A 100% score against
your own answer key proves nothing about generalization. The team went looking for real,
external ground truth already sitting unused in the repo (the CUAD dataset, cloned early but
never actually used to check anything), built a real evaluator against it, and got an honest
first number: **37.7% recall**. That number was then used — not hidden — to find and fix five
specific clause-detection gaps, each verified against the actual contract text that exposed it,
re-measured against all 510 contracts each time, landing at the final **42.2% / 92.7%** headline
above. This one change is the difference between a demo that looks good and a result a stranger
can independently check.

### An experiment that was built, then deliberately deleted

The team built ~600 lines of keyword-grep "strictness judge" scripts meant to give a fast, free
self-graded score to iterate against. What it actually taught them: a heuristic that checks
whether a file *contains a word* is trivially gameable (add the word "async" in a comment, gain
a point) — and worse, it had already produced a false claim ("100/100, 0 faults") that got
published into the product itself. The scripts were deleted, not patched, and the earlier false
claim was corrected in the same changelog entry that explains why.

### Real human-in-the-loop, built in direct response to critical feedback

An internal strict-review audit (a separate AI reviewer briefed to act like a skeptical judge,
with no incentive to be generous) flagged that the "human review" step was, at the time, a
pure stub — a log line claiming a pause would happen, with no real pause. The team built the
real thing: a genuine LangGraph `interrupt()` call that actually halts program execution when
a finding is rejected, with a real payload a human can review and override, and a real
`Command(resume=...)` call that continues the exact paused run. Building and testing this
surfaced four real, previously-hidden bugs — each found only by testing at a MORE realistic
level than the one before (first testing the graph node directly, then the full HTTP API, then
the actual dashboard UI a person would click through) — a pattern repeated throughout this
project: verify claims by actually running them, not by inspecting the code and assuming.

### Closing the loop: LLM-as-generator, and a second audit that caught real bugs in it

The same strict-review process was then pointed at the newly-built LLM-as-generator feature
itself, cold, the same day it was written — and found three more real, concrete problems (a
dashboard badge showing the wrong on/off state, a test that didn't actually prove its own
central claim, and an edge case in the anti-hallucination substring-matching logic that could
anchor to the wrong location in a document with repeated boilerplate phrasing). All three were
fixed and re-verified with new regression tests before submission. This "build it, then have a
second skeptical pass try to break it" loop is the project's core discipline, applied to itself
one more time in the final hour before submission.

---

## 9. Test coverage and reproducibility (why the numbers above can be trusted)

- **97 automated tests, zero failures**, across three real test suites (`advanced/` unit +
  integration, `baseline/`, and a real dashboard smoke suite that actually drives the Streamlit
  UI's buttons and checkboxes via `streamlit.testing.v1.AppTest`, not just imports the module).
- **`mypy --strict` clean across all 22 source files** in the advanced engine — this was not
  always true; an earlier changelog entry documents finding the strict-mode badge had been
  claiming a pass while mypy wasn't even installed, and fixing 106 real type errors to make the
  claim true.
- **Every number in this document is generated by a script, not hand-typed** — the same
  discipline `evidence/benchmarks/comparison.md` states in its own header. Re-run any of them
  from a clean checkout: `make setup && make reproduce`.
- **No API key required to reproduce the certified numbers.** `EVAL_MOCK=1` (the default for
  reproduction) makes the entire pipeline fully deterministic and $0 — a judge with no
  configured provider key sees the exact same numbers reported here.

---

## 10. What this project explicitly does NOT claim (stated on purpose, not omitted)

- It does not claim to beat GPT-4.1 or a fine-tuned transformer on the harder exact-span-match
  task — the comparison table above is a neighborhood check, not a leaderboard claim.
- It does not claim the semantic embedding layer's +6.8pp recall number is settled — it is a
  real result from real embeddings, but on only 7 real contracts (repeatedly blocked from a
  larger run by free-tier API quota, honestly disclosed each time it happened rather than
  hidden or worked around with a smaller mock sample presented as full-scale).
- It does not claim the LLM-as-generator layer has been validated at CUAD scale — unlike the
  $0 BM25 layer, which got a full 510-contract sweep, the LLM layer has exactly one real,
  successful, non-mocked call as its evidence: an honest existence proof that the mechanism
  works end-to-end, not a recall-improvement claim.
- It does not claim 100% recall anywhere, on any metric, after the "Is Trap Recall Fake?"
  correction — several individual clause types remain under 30% recall against real ground
  truth, and the README says so directly next to the numbers, not in fine print.
- It does not auto-apply any edit to a contract, in either baseline or advanced, under any
  configuration. Every finding — however verified — routes to a human decision.

---

## 11. Suggested narration arc (for whoever is producing the video from this document)

1. **Open on the problem** — the 24-month renewal / 30-day notice trap, concretely described,
   and why it's easy to miss in an 80-page document under deadline pressure.
2. **Introduce the two solutions** — baseline as an honest floor, advanced as the real system,
   and the hackathon's actual rule that both must exist and be honestly compared.
3. **Walk the pipeline** — extract → risk → verify → human review, with the anti-hallucination
   design as the through-line: nothing is shown to a human without a real, checked citation.
4. **Land on the headline number** — 42.2% vs 15.5% recall, 92.7% vs 53.7% precision, on 510
   real, independently-labeled contracts — and why that independence is the whole point.
5. **Tell one real development story** — "Is Trap Recall Fake?" works well: it shows the team
   catching its own inflated self-graded metric and replacing it with a real, lower, honest one.
6. **Show the agentic depth** — the LangGraph engine, the Reflection pattern, the real
   human-in-the-loop pause, and the LLM-as-generator layer's own strict evidence gating.
7. **Close on discipline, not just features** — 97 passing tests, a repeated pattern of
   self-auditing and fixing real bugs before submission, and an explicit list of what is NOT
   claimed. The honesty is itself the pitch: a system built to say "I don't know" rather than
   guess is exactly what the problem (a reviewer who cannot afford to be misled) actually needs.

**Supplementary visual assets** (already generated, real, sourced from the same evidence files
this document cites): `evidence/benchmarks/charts/headline_recall_precision.png`,
`per_rule_recall.png`, `changelog_progression.png`, `test_health.png`. Regenerate any time with
`python scripts/generate_charts.py`.
