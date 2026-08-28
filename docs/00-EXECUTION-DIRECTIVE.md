# Project Execution Directive — micro1 Agentic Workflows Hackathon

> **Source of truth:** [`PROBLEM.md`](../PROBLEM.md) (extracted from official PDF) + judging criteria below.  
> **Objective:** Not merely to build something that works — to build a **practical, technically strong, measurable, reproducible, differentiated agentic workflow with a credible path to winning**.  
> **Target:** **Top 3 minimum, 1st place intent.** Every decision is judged against that bar.  
> **Authority:** This directive is the *process*; `PROBLEM.md` is the *problem*. If they conflict, `PROBLEM.md` wins.

Use the **micro1 Agentic Workflows Hackathon problem statement and judging criteria as the primary source of truth for every project decision**.

---

## The Four Questions (answer continuously)

| # | Question | Where it is proven |
|---|----------|--------------------|
| **01** | **Who has this problem?** | `README.md` → Intended user + `docs/problem-brief.md` |
| **02** | **What bottleneck makes it worth solving?** | `README.md` → Bottleneck + `CHANGELOG.md` baseline |
| **03** | **Does the agent solve it well?** | `evidence/benchmarks/comparison.md` + `scripts/eval.py` |
| **04** | **Can another person reproduce the result?** | `REPRODUCTION.md` + `make reproduce` + `evidence/benchmarks/reproduce.log` |

Final deliverables must also satisfy the four required artifacts: **code + changelog · reproduction guide · video · trajectories** (`PROBLEM.md` §7).

---

## Phase 0 — Understand the Problem Before Building

**Do not write implementation code yet.**

Read `PROBLEM.md` completely and extract:

- Intended user, concrete real-world problem, current workflow / baseline process
- Specific bottleneck, why it matters, what a successful outcome means to the user
- Where an agent can genuinely improve the workflow
- Constraints, ground rules, ethical considerations, reproducibility requirements
- The **six judging dimensions and weights** (see §Judging below)
- Required submission artifacts (four items)

**Artifact:** Concise **Problem Definition** (`docs/problem-brief.md`) that lets a reviewer immediately understand:

> *“This person currently struggles with X because of Y, causing Z. Our agentic workflow improves this by doing A, B, and C, producing measurable improvement on D.”*

> Do not drift into solving a broader or different problem because it is technically interesting.

**Gate:** `docs/problem-brief.md` committed + `ARCHITECTURE.md` §7–8 checked + `PROBLEM.md` clean extraction verified.

---

## Phase 1 — Validate the Project Direction

Before implementation, **score the proposed idea** against the actual rubric — be ruthlessly honest.

### 1. Problem & User Value — 15 pts
- Clearly identifiable user? Meaningful (not artificial) problem? Concrete bottleneck?
- Would a real user want this solved? Value understandable in seconds?
- Solving a **painful part** of the existing process vs. adding complexity?

### 2. Agent Solution & Engineering — 30 pts
- Why does this need an agent? Which capabilities genuinely help?
- Would **better context / tools / memory / verification / skills / orchestration** actually improve the result?
- Every component must have a **measurable purpose**. No decorative complexity.

> **Do not add agents merely to look sophisticated.** Use the smallest set that produces the strongest measurable result.

### 3. End-to-End Quality — 20 pts
Output should feel like something a real person would **sign their name to**, not an obvious AI draft. Evaluate: quality, completeness, reliability, UX, error handling, edge cases, consistency, explainability, trust.

### 4. Measured Improvement — 15 pts
Improvement over a *fair* baseline. Define evaluation **before** optimizing. Same cases for baseline vs. agent vs. variants. Prefer **10+ cases** including **one deliberately difficult case**.

### 5. Reproducibility — 15 pts
Clean-environment repeatability: install, deps, config, data, commands, model/provider, evaluation, expected outputs, runtime, cost, versions.

### 6. Hot Take / Insights — 5 pts
Turn an **observed failure** into a lesson: *What failed → why → what changed → what this teaches about building better agents.*

**Gate:** Self-score with evidence refs. If any dimension lacks evidence, re-scope before Phase 2.

---

## Phase 2 — Conduct Deep Research

Broad, technically serious research — not surface blog posts.

**Investigate where relevant:** academic papers, SOTA, agent architectures, planning & orchestration, tool-use, verification/self-correction, memory, retrieval/context, benchmarks, evaluation methods, human-in-the-loop, OSS implementations & GitHub repos, engineering writeups, case studies, expert + community (Reddit) discussions, adjacent products, known failure modes and failed approaches.

For each approach: **What it does → why it works → where it fails → whether it applies → whether we can improve on it.**

Actively search for: weaknesses, evaluation gaps, reliability problems, cost/latency trade-offs, naive-agent failures, intelligent combinations, and a **small but demonstrable innovation**.

Clearly separate: *established evidence vs. research findings vs. engineering best practice vs. our inference vs. our proposed innovation.*

> Do not blindly copy. Improve.

**Artifacts:** `docs/10-RESEARCH-PROTOCOL.md` + `docs/research/*.md` per thread + synthesis with differentiation thesis.

---

## Phase 3 — Establish a Fair Baseline

Before the final architecture, implement a **simple baseline** representing a reasonable non-agentic (or minimally agentic) way to handle the task:

- Direct prompt · basic single agent · simple script/template · manual workflow

**Same task + same evaluation cases** as the final system. Document: architecture, instructions, tools, model, inputs, outputs, evaluation method, **baseline score, runtime, cost**.

> Do not create an artificially weak baseline to inflate improvement. A skeptical judge must accept it as fair.

---

## Phase 4 — Create the Research-Backed Implementation Plan

Only after problem analysis, research, and baseline definition — finalize the full plan:

### Product / Workflow
Intended user, journey, inputs/outputs, human checkpoints, failure behavior, user-facing experience.

### Agent Architecture (precise)
Number of agents, responsibilities, instructions, tools, shared/context state, memory, retrieval, verification, orchestration, retry/escalation, human approval points.

> For every component: *Why does it exist, and what evidence suggests it improves the result?* Remove what cannot justify itself.

### Technical Implementation
Models, frameworks, APIs, libraries, data structures, storage, retrieval, tool interfaces, evaluation infra, logging, observability, testing. Prefer **reliable & reproducible** over complex.

### Evaluation
**Primary metric** (user success) + secondary (quality, accuracy, completion rate, human time, cost/latency, error/reliability/consistency). Scoring rubric precise enough for independent replication.

> The plan is not final at v1. Review it against problem, research, judging criteria, feasibility, demo potential. Iterate until coherent, defensible, executable.

**Artifact:** `docs/11-IMPLEMENTATION-PLAN.md` (copy from `11-IMPLEMENTATION-PLAN-TEMPLATE.md`).

---

## Phase 5 — Build an Improvement Changelog (first-class deliverable)

Start: **Baseline → Iteration 1 → Iteration 2 → … → Final**

For every meaningful experiment:

| Stage | What changed | Why | Evidence | Decision | Learning |
|-------|--------------|-----|----------|----------|----------|
| Baseline | Simple initial approach | Establish reference | Result | — | Starting point |
| Iteration 1 | … | Address observed problem | Result | Kept/revised/removed | … |
| Iteration 2 | … | Address failure | Result | Kept/revised/removed | … |
| Final | Combined successful changes | Maximize performance | Final result | Kept | Main contribution |

**Removed experiments are important** — do not hide failures. The changelog should make clear: *“Observed failure X → introduced change Y → measured improvement Z → retained Y.”*

**Artifact:** `CHANGELOG.md` (and `docs/00-...` §Traceability).

---

## Phase 6 — Implement Incrementally

1. Minimum viable workflow
2. Baseline evaluation
3. One meaningful improvement → evaluate → record → keep/modify/remove
4. Repeat

**Maintain:** clean structure, strong typing where appropriate, meaningful tests, clear config, structured logging, reproducible experiments, **version-controlled prompts, agent instructions, evaluation cases & results**, documented decisions.

**Avoid:** hard-coded secrets, undocumented manual steps, magic constants, one-off hacks, hidden deps, evaluation leakage, changing evaluation to inflate scores.

---

## Phase 7 — Adversarial Evaluation

Construct **difficult cases** that expose: ambiguous/missing/conflicting information, long context, tool failures & incorrect outputs, hallucinations, loops, bad plans, wrong assumptions, edge cases, adversarial inputs, verification gaps, multi-agent disagreement.

Measure **where the system fails**. Determine: *Can this be fixed technically?* If yes, fix & re-evaluate. If not, make the limitation explicit. **Never disguise a known failure as success.**

---

## Phase 8 — Reproduction Dry Run (clean-room)

Pretend you are a new contributor. From a **clean environment**, verify: repo setup, deps, env config, data prep, model config, baseline & agent execution, evaluation, tests, demo, output generation.

Record: **exact commands, required files, env vars, versions, runtime, cost, expected outputs.** Fix every reproducibility issue.

> The README must let another person reproduce the core result **without asking the developer**.

**Artifact:** `REPRODUCTION.md` + `evidence/benchmarks/reproduce.log` + `make reproduce` green.

---

## Phase 9 — Final Hackathon Review (multiple independent lenses)

### Technical Reviewer
Architecture sound? Agents necessary? Tools effective? Orchestration justified? Failure handling strong? Maintainable?

### Research Reviewer
Claims evidence-backed? Evaluation defensible? Innovation differentiated? Experiments informative? Limitations acknowledged?

### Hackathon Judge
Problem immediate? User obvious? Bottleneck meaningful? Agent genuinely useful? Clear improvement over baseline? Demo compelling? Memorable?

### Skeptical Competitor
*“If another team wanted to beat us, what would they criticize?”* Address it.

### End User
Would I use it? Intuitive? Output good enough to act on? Saves meaningful effort? Where would trust stop?

### Reproducibility Reviewer
*“Could I reproduce the headline result without contacting the team?”*

### Demo Reviewer
*“Can the strongest value be understood in 60–90s?”*

---

## Phase 10 — Prioritize and Fix Weaknesses

Categorize every finding:

- **MUST FIX** — blocks correctness, reliability, judging criteria, reproducibility, or credibility
- **SHOULD FIX** — materially reduces quality/score/competitiveness
- **NICE TO HAVE** — useful, low ranking impact
- **SAFE TO LEAVE** — negligible

Fix all **MUST FIX** + high-impact **SHOULD FIX**, then re-test & re-evaluate.

---

## Phase 11 — Optimize for the Actual Scoring Rubric

Produce a conservative internal scorecard (evidence required for every point):

| Criterion | Max | Current assessment | Evidence | Remaining gap |
|-----------|-----|--------------------|----------|---------------|
| Problem & User Value | 15 | | | |
| Agent Solution & Engineering | 30 | | | |
| End-to-End Quality | 20 | | | |
| Measured Improvement | 15 | | | |
| Reproducibility | 15 | | | |
| Hot Take / Insights | 5 | | | |
| **Total** | **100** | | | |

> Do not award points because it “sounds good.” Award only with convincing evidence. Be conservative.

---

## Phase 12 — Final Deliverables

Repository must contain everything for the four official items (`PROBLEM.md` §7):

1. **Complete Solution Code + Improvement Changelog** — code, agent instructions, config, evaluation, tests, README (user + bottleneck + value), baseline, changelog, results, main failure mode, hot take.
2. **Reproduction Guide** — clean-environment setup, install, config, data, baseline/solution/evaluation commands, expected outputs, versions, runtime, cost.
3. **Solution Video** (≤5 min) — **Problem → User → Bottleneck → Baseline → Agent Solution → Realistic Execution → Measured Improvement → Key Changelog Insight → Differentiation** (strongest result visible quickly; not architecture-first).
4. **Agent Trajectories** — representative for **every agent** (instructions → input/context → reasoning/actions → tool calls/responses → verification → retries/failures → human checkpoints → final result). Choose trajectories that demonstrate architectural value, not just trivial successes.

---

## Final Gate

Do not declare complete after “it works.” Answer honestly:

- Does this clearly solve a meaningful problem for a specific user?
- Is there a credible, fair baseline showing measurable improvement?
- Can we explain which engineering decisions caused that improvement?
- Is the final output genuinely useful, not just demo-impressive?
- Is the agent architecture purposeful, not unnecessarily complex?
- Can another person reproduce the main result from a clean environment?
- Does the project have a technically defensible point of differentiation?

> **If submitted to the micro1 Agentic Workflows Hackathon today, is there a credible evidence-based reason judges would place it in Top 3?**

> **What specifically prevents it from being #1?**

Do not accept vague answers (“more polish”). Identify the **specific highest-impact weakness**. If fixable, fix it. Then:

**Review → Identify weakness → Prioritize → Implement → Test → Evaluate → Reproduce → Review again**

Repeat until no high-impact weakness remains.

---

## Core Operating Principle

Throughout, optimize for:

**Real problem → Purposeful agent design → Measurable improvement → Evidence → Reproducibility → Strong demo → Judgeability**

Do **not** optimize for:

**More agents → More features → More code → More complexity**

> The winner is not the most sophisticated architecture on paper. It is the one that most convincingly demonstrates: *A real person had a meaningful bottleneck. A carefully designed agentic workflow solved it better than a reasonable baseline. The improvement is measurable. Design choices are evidence-justified. The result is polished enough to use. And another person can reproduce it.*

---

*This directive governs all contributors (human + agents) until submission. `PROBLEM.md` is the problem truth; this document is the execution truth.*
