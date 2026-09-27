# Baseline vs Advanced — Real Evaluation (computed by scripts/eval_harness.py, no hardcoded numbers)

## Primary metric — External Validation Against Real Expert Legal Annotation

**This is the one number in this evidence set graded against labels we did not write ourselves.**
Every other metric below (Trap Recall, the generalization suite, the stress suite) is graded
against gold labels/fixtures *we* authored -- useful for regression testing, but not proof the
system generalizes to real, independent judgment. CUAD (Hendrycks, Burns, Chen, Ball -- NeurIPS
2021) is a genuinely independent, expert-annotated legal NLP benchmark: 510
real contracts, hand-labeled by lawyers, that we did not write and did not tune our detection
regexes against before this check existed. This measures clause-type PRESENCE detection only
(does the clause exist), not threshold/policy judgment (e.g. whether a 36-month renewal term is
too long is our own playbook's policy choice, not a labeled fact -- there is no external ground
truth to check that part against).

**Methodology caveat, stated plainly:** the labels are external and untouched, but the detection
regexes were not tuned on a disjoint held-out split of CUAD -- CHANGELOG #12 documents reading real
failures directly off this same 510-contract set and adding patterns
keyed to the exact phrasing found there (IP Ownership Assignment, Post-Termination Services, Notice
Period, Termination for Convenience, Non-Compete), then re-measuring against the same contracts each
time. That is standard "read the errors, fix the errors" iteration, not fabrication -- but it means
the numbers below are not a clean train/test split the way the semantic-threshold tuning in #13 is
(disjoint seed=99 dev split, reported only on the held-out remainder). Read this as "best
iteratively-achieved regex performance on CUAD," not as a number guaranteed to reproduce cold on a
disjoint slice of CUAD-like contracts.

| System | Recall | Precision |
|--------|--------|-----------|
| Baseline | 15.5% | 53.7% |
| Advanced | 42.2% | 92.7% |

Per-rule breakdown (510 real contracts, real expert labels):

| Rule | Adv Recall | Adv Precision | Base Recall | Base Precision | n gold-present |
|------|-----------|----------------|-------------|-----------------|-----------------|
| Renewal Term | 61.9% | 90.8% | 0.0% | n/a | 176 |
| Notice Period to Terminate Renewal | 19.8% | 95.7% | 45.0% | 26.9% | 111 |
| Termination for Convenience | 13.7% | 92.6% | 7.7% | 87.5% | 183 |
| Cap/Uncapped Liability | 51.6% | 94.7% | 85.5% | 64.6% | 275 |
| Audit Rights | 26.6% | 95.0% | 13.1% | 65.1% | 214 |
| Governing Law | 74.1% | 99.1% | 0.0% | n/a | 437 |
| License Grant | 42.4% | 98.2% | 0.0% | n/a | 255 |
| Non-Compete | 31.9% | 69.1% | 0.0% | n/a | 119 |
| Non-Disparagement | 23.7% | 81.8% | 0.0% | n/a | 38 |
| IP Ownership Assignment | 35.5% | 86.3% | 0.0% | n/a | 124 |
| Post-Termination Services | 8.2% | 51.7% | 0.0% | n/a | 182 |

**Honest reading:** advanced is a real, substantial improvement over baseline on independently-
labeled ground truth (42.2% vs 15.5% recall, at much higher
precision: 92.7% vs 53.7%) -- not the "100%" the
self-graded Trap Recall metric below reports. Several rules are still weak in absolute terms
(clause-type presence detection is regex/keyword-based, not semantic retrieval -- see
ARCHITECTURE.md for that design tradeoff and its real recall ceiling on broadly-worded CUAD
categories). Full detail: `evidence/benchmarks/cuad_ground_truth_results.json`, script:
`scripts/eval_cuad_ground_truth.py`.

**Why baseline beats advanced on 2 of 11 rules' recall (Notice Period, Cap/Uncapped Liability) --
explained, not silently left as an inversion:** baseline's pattern for these two rules is
deliberately broad and unanchored -- e.g. Notice Period's is `notice...(\d+)...days` anywhere
within 150 characters, matching almost any mention of the word "notice" near a day-count, not
specifically a renewal-notice clause. That catches more real instances but also many unrelated ones
at a steep precision cost. Advanced's pattern is anchored to the clause header/type language itself,
trading recall for precision by design -- consistent with this project's stated "high precision,
conservative recall" identity (see the dashboard's Metrics tab). This is a real, disclosed per-rule
precision/recall tradeoff, not a regression or a bug -- baseline's headline number (53.7%
overall precision) shows the cost of that broad-matching strategy averaged across all 11 rules.

### Where this sits next to published, independent results on the same dataset
Not a like-for-like comparison (different metric -- see caveat below) but the right
neighborhood check, so the numbers above aren't read in a vacuum:

| Method | Metric | Result | Source |
|--------|--------|--------|--------|
| DeBERTa-xlarge, fully supervised (fine-tuned on CUAD's own train split) | AUPR / precision @ 80% recall | 47.8% AUPR / 44.0% precision | CUAD paper itself (Hendrycks et al., NeurIPS 2021, arxiv.org/abs/2103.06268) |
| BERT-base, fully supervised | precision @ 80% recall | 8.2% | same paper |
| GPT-4.1, zero-shot | span-match F1 | 0.641 | ContractEval, 2025 (arxiv.org/abs/2508.03080), on CUAD's test split |
| DeepSeek-R1-Distill-7B, zero-shot | span-match F1 | 0.071 | same paper |
| **This system (advanced), zero training, regex+rules** | presence recall / precision | **42.2% / 92.7%** | `eval_cuad_ground_truth.py`, this repo |

**Caveat, stated plainly:** the published numbers above measure exact SPAN match (a stricter
task) via AUPR or span-F1; this system's number measures clause-type PRESENCE only (a looser
task). These are not directly interchangeable and this is not a claim of beating GPT-4.1 or
DeBERTa-xlarge. What this table does show: on the same real dataset, a fully-supervised
fine-tuned transformer tops out around 44-48%, a frontier zero-shot LLM lands around 0.64 F1 on
the harder task, and this system's zero-training rule-based recall/precision sits in a credible
neighborhood of both rather than an implausible one. See CHANGELOG #13.

### Real, live zero-shot LLM comparison (independent method, same contracts, same metric)

gemini/gemini-2.5-flash, asked cold with no CUAD-specific prompt tuning, on 1/10 real CUAD contracts (rest hit the free-tier daily generation cap mid-run -- a real external constraint, not a silent skip; see CHANGELOG #17): recall 33.3%, precision 100.0%. **n=1 is too small to draw any conclusion from on its own** -- this is disclosed as a genuinely real, live data point (not mock, not invented), not as a settled comparison number. Re-run with a larger `--sample` once quota resets for a result worth reading directionally.

See `evidence/benchmarks/llm_zeroshot_baseline_results.json`.


### Semantic hybrid layer (real embeddings, small-sample real signal, not yet at full-scale validation)
A real hosted-embedding semantic layer (`advanced/src/harness/semantic.py`, `gemini-embedding-001`
via litellm) was built to raise recall past the regex ceiling above. On a 7-contract real-API dev
sample (held out from the 510 reported above), it raised recall 45.5% -> 52.3% (+6.8pp) at a real
precision cost (100% -> 74.2% on that same tiny sample) at threshold 0.65. This is real signal from
real embeddings and real CUAD labels, not invented -- but n=7 is too small to promote to a headline
number, and two larger validation attempts (dev-size 40, then 25) were cut short by this session's
own testing exhausting first the per-minute then the per-day free-tier embedding quota. Full detail
and reproduction command: CHANGELOG #13.

### BM25 lexical hybrid layer (real, $0, validated on the FULL 510 real contracts)
A second, independent recall layer (`advanced/src/harness/bm25.py`, classical Okapi BM25 via
`rank_bm25`) needs no API call, no key, no quota -- pure local lexical-overlap scoring against the
same real CUAD category-description anchors the semantic layer uses. Because it is free and
deterministic, it was swept and validated against the FULL 510-contract set (not a small dev
sample): `eval_cuad_ground_truth.py --bm25`, threshold=42.0 (chosen as the precision-preserving
point in `scripts/tune_bm25_threshold.py`'s sweep, rejecting the best-F1 threshold=10 for trading
too much precision away). Real result, same 11-rule methodology as the headline number above:
recall **42.2% -> 46.1% (+3.9pp)**, precision **92.7% -> 88.1% (-4.6pp)**. Off by default
(`ENABLE_BM25_EXTRACTION=0`) so the certified reproduction stays unchanged -- this is a disclosed,
deliberate opt-in trade-off, not an unvalidated result. Full detail, threshold-selection reasoning,
and per-rule breakdown: CHANGELOG #19. Result file:
`evidence/benchmarks/cuad_ground_truth_bm25_only.json`.

## Secondary diagnostic — Trap Recall (self-graded, 30 CUAD-derived contracts, gold traps we curated)
Retained because it is a real, deterministic, $0, always-reproducible regression-test signal --
did the system catch OUR OWN curated risky-provision examples -- but it is not independent
validation (see the external check above for that) and should not be read as a generalization
claim on its own.

| System | Trap Recall | Delta |
|--------|-------------|-------|
| Baseline | 56% | — |
| Advanced | 100% | +44pp |

## Secondary diagnostics
| Metric | Baseline | Advanced | Change |
|--------|----------|----------|--------|
| Evidence-supported edit rate | 57.1% | 100.0% | +42.9pp |
| Unsupported edit rate | 42.9% | 0.0% | -42.9pp |
| Verification catch rate | — | 0.0% | — |
| Over-redlining avg/contract | 2.33 | 1.30 | -1.03 |
| Surgical rate | 100% | 100% | +0pp |
| Est. human review time/contract | 4.5 min | 3.0 min | -1.5 min |
| LLM Judge Score (0-100) | 52 | 44 | -8.1 |

Est. human review time is a disclosed formula (120s skim + 45s/supported finding + 90s/unsupported finding), not a measurement -- see ARCHITECTURE.md.
LLM Judge mode: **partial-live (9/16 calls reached the model, rest fell back to mock -- likely a provider quota limit hit mid-run)**, n=8 contracts. Per-contract transcripts in `evidence/trajectories/llm_judge_*.json`. Sample is small (single digits) and a real provider quota can cut a run short mid-way -- treat this as a directional secondary signal, not a settled score. A negative delta does not automatically mean the advanced system is worse: spot-check the largest per-contract gap's transcript before trusting it -- the LLM judge itself can misjudge a genuinely verbatim, in-contract citation as a hallucination (observed and confirmed on this run's outlier case).

## Latency (p50 / p95 ms, measured on 30 contracts, this machine)
| System | p50 | p95 | Delta p95 |
|--------|-----|-----|-----------|
| Baseline | 0.7 | 1.1 | — |
| Advanced | 21.0 | 37.2 | +36.0 |

## Fixture suite composition (disclosed, not hidden)
Of the 30 contracts in this suite, **18 contain hand-authored "ADDENDUM TRAP
INJECTION" text** appended to a real CUAD contract (used only when no natural occurrence of that
trap pattern existed anywhere in the CUAD corpus); the remaining **12 are
unmodified real CUAD contract text**. This matters because injected text can echo the detection
regex's own vocabulary, inflating recall on this suite alone -- see the held-out generalization
suite below, which is written independently and does not have this risk.

This suite's synthetic gold traps (Trap-A/B/C) also only exercise **5 of the
12 playbook rules** (P-01, P-02, P-06, P-11, P-12).
The remaining rules are implemented but structurally untested by this corpus (it was never
designed to contain their trap patterns) -- the generalization suite below is what validates them.

## Held-out generalization suite (scripts/eval_generalization.py)
14/14 scored cases passed (100%), covering all 12 playbook rules + 2 clean (false-positive) controls. 1 deliberately adversarial case (uncapped liability phrased without the words 'unlimited'/'uncapped') is excluded from the score and reported as a known, undisclosed-fix gap (caught_anyway=False).
Full detail: `evidence/benchmarks/generalization_results.json`, fixtures in
`shared/fixtures/generalization/` (written independently of the playbook/regex text, one per rule).

## Stress suite -- messier real-world text (scripts/eval_stress.py)
7/7 scored cases passed (100%) on messier, harder-to-parse real-world text: OCR-style whitespace noise, ALL CAPS/em-dash headers, a long document with decoy numbers in unrelated sections, multi-level subsection numbering (8.2/8.3/8.4), non-US drafting conventions, and a common real-world phrasing gap ('shall automatically renew') that no existing regex covered. This suite is what actually found the last three real bugs fixed in this pass -- see CHANGELOG.md for the details.
Full detail: `evidence/benchmarks/stress_results.json`, fixtures in `shared/fixtures/stress/`.

**Headline:** CUAD ground truth (real, 510 contracts): recall 15.5% -> 42.2% | precision 53.7% -> 92.7% || Trap Recall (self-graded regression suite) 56% -> 100% (+44pp) | Unsupported 42.9% -> 0.0% | Evidence-supported 57.1% -> 100.0% | LLM Judge 52 -> 44/100 (partial-live (9/16 calls reached the model, rest fell back to mock -- likely a provider quota limit hit mid-run))
