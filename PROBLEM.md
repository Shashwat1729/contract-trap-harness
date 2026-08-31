# micro1 — Agentic Workflows Hackathon — Official Problem Statement

> **Source:** [`micro1 - First Hackathon97ce7c5.pdf`](micro1%20-%20First%20Hackathon97ce7c5.pdf) (10 pages, 648 KB) — extracted 2026-08-28, 14,279 chars, official PDF included in this repository for provenance.

> **Nature of challenge:** Open-ended. You choose a specific, meaningful problem you understand. Judges evaluate on the four questions and six criteria below — not on a single prescribed task.

---

## 1. Welcome & Challenge

**Host:** micro1 — Agentic Workflows Hackathon

> Choose a problem worth solving and use agents to create something people would genuinely find useful. Keep it practical, share what you learn and have fun.

**Your challenge:**
Pick a **specific and meaningful problem you understand**. Use agents to solve it and **show through clear evidence** that your solution improves the way the task is handled today.

Start by explaining:

- Who has the problem
- The bottleneck they face
- Why solving it would be valuable in practice

> The goal is to create something a real person would want to use.

### The Four Questions (keep in mind throughout)

| # | Question |
|---|----------|
| **01** | **Who has this problem?** |
| **02** | **What bottleneck makes it worth solving?** |
| **03** | **Does the agent solve it well?** |
| **04** | **Can another person reproduce the result?** |

---

## 2. How Agents Can Help

Use **whichever agent capabilities help solve the problem well**. Examples:

- Better **context** or better **tools** improve some solutions
- **Memory** to carry important information forward
- **Verification** to catch errors before they reach the user
- **Specialized skills** to deepen ability in a particular task
- **Orchestration** across several agents for some solutions

> Choose the approach that fits your problem. Judges focus on **whether each design choice improves the solution** and helps the agent reach the goal reliably. **Purposeful choices matter more than the number of components.**

### Show How the Solution Improved — Baseline vs. Agent

Create a **simple baseline** that represents a reasonable basic way to handle the task *before* using your solution. Examples:

- One direct prompt with basic instructions
- One general-purpose agent with basic tools
- A simple script or template
- The manual process people use today

**Keep the comparison fair** — give the baseline and final solution the **same task and evaluation cases**. Explain any meaningful difference in the resources available to each one.

Use the final baseline comparison to show the **size of overall improvement**. Use the **changelog** to explain **where that improvement came from**. Together they tell the complete story.

---

## 3. Tell the Story with an Improvement Changelog

Create a short changelog that tells the story of how your solution evolved. **Start with the simple baseline and follow the journey through to the final result.** Each meaningful change must be clear in its contribution.

**Add one entry for every important experiment.** Explain what you tried and why. Show the result using the **same evaluation method** whenever possible and share what you decided to do next. **Include experiments you later removed** and explain what they taught you.

### Example progression (replace with your actual changes)

| Stage | What you tried and why | Evidence | Decision / Learning |
|-------|------------------------|----------|---------------------|
| **Baseline** | Started with [basic approach] | [baseline result] | Established the starting point |
| **Iteration 1** | Added a skill to address [issue] | [new result] | [kept, revised or removed] |
| **Iteration 2** | Added verification after observing [failure] | [new result] | [kept, revised or removed] |
| **Iteration 3** | Changed orchestration to improve [goal] | [new result] | [kept, revised or removed] |
| **Final** | Combined the changes that worked | [final result] | Identified the main contribution |

> **Do not hide failed experiments** — a strong changelog shows: *"Observed failure X → introduced change Y → measured improvement Z → retained Y."*

---

## 4. How to Evaluate Your Solution

**Choose one primary metric** that reflects what **success means to the user**.

- Developer → tests passing
- Operations → time saved / cost reduced
- Forecasting → calibration

Pick the measure that best captures the improvement your solution promises.

**Before running the evaluation**, define what a good final result looks like for the intended user. **Use the same cases for both baseline and final solution**, then share the **complete results**.

- Target **10 or more cases** when the task allows it
- **Include at least one challenging case** and explain what it revealed

### Simple format you can use

| Metric | Simple baseline | Agent solution | Change |
|--------|-----------------|----------------|--------|
| Primary outcome | [value] | [value] | [change] |
| Human time per task | [value] | [value] | [change] |
| Cost per task | [value] | [value] | [change] |

> You run this evaluation yourself. If the format fits poorly, **design your own clear scoring rubric** and propose it so judges can use it.

---

## 5. How Judging Works — Score out of 100

Each row describes what **strong work** looks like. Use the question at the end to self-check before submitting.

| Criterion | Points | What strong work looks like | Self-check question |
|-----------|--------|----------------------------|---------------------|
| **Problem & User Value** | **15** | Solves a meaningful problem for a clearly defined user | *Who experiences the bottleneck and why does solving it matter?* |
| **Agent Solution & Engineering** | **30** | Uses agents **purposefully** and is technically sound. Better context/tools may help one project, while memory/verification/skills/orchestration may help another | *Which design choices helped the agent solve the problem?* |
| **End-to-End Quality** | **20** | Completes a **realistic, self-contained execution** and produces a final result the user can use — polished, trustworthy, not an obvious AI draft | *Would the intended user consider this output high quality, or does it read as clearly AI-generated?* |
| **Measured Improvement** | **15** | Demonstrates **gains over a fair baseline** and uses the changelog to connect each iteration with evidence | *Which changes truly improved the outcome?* |
| **Reproducibility** | **15** | Gives another person a **clear path** to run the solution and baseline and reach the main result from a clean environment | *Could they do it from a clean environment?* |
| **Hot Take / Insights** | **5** | Turns an **observed failure mode** into a practical lesson for building more reliable agents | *What did you learn and how would it change what you build next?* |
| **Total** | **100** | | |

---

## 6. Ground Rules — Baseline Requirements for Every Eligible Project

1. You are welcome to build with tools and components you already know.
2. Make it clear **what existed before** the competition and **what you added**.
3. Use every tool/component according to its **license and service terms**.
4. Keep **consequential actions** controlled through a **sandbox/simulation**. Add **human approval** before the action happens.
5. Make a **qualified human reviewer** part of any solution that could significantly affect someone.
6. Choose a **legal and ethical** use case that treats people and their data responsibly.
7. Use information you are **allowed to share**. **Public or synthetic data** are usually easiest; **approved anonymous data** also works.
8. Keep **credentials and private information** outside the submission.
9. **Connect every claim** about your results to the evidence you submit.
10. Give judges **enough access to run the project** and reproduce the main result.

---

## 7. Final Deliverables — The Four Required Items

### 01 — Complete Solution Code and Improvement Changelog
Share the full project and everything required to run it. Include:
- Code **and** the **instructions that shape each agent**
- README: introduce the **intended user**, explain **current bottleneck**, describe **why solving it is valuable**
- **Clearly labeled Improvement Changelog** (structure from §3) — one entry per meaningful iteration, connected to the evidence that guided your next decision
- Close with the **main failure mode** and your **hot take**

### 02 — Reproduction Guide
Written for **someone starting from a clean environment**:
- Setup steps
- Exact commands for the **solution, baseline, and evaluation**
- Which data is required and what output to expect
- Relevant **versions, approximate runtime and cost**

### 03 — Solution Video (up to 5 minutes)
- Begin with the **problem and simple baseline**
- Walk through **one realistic execution from start to finish**
- Show the **final comparison** and briefly explain the **changelog**
- Highlight the **change that contributed most** and **one experiment you removed**

### 04 — Agent Trajectories
Include **representative trajectories for every agent you used**:
- Easy to follow from **agent instructions → final result**
- Show **what the agent did** and **how its tools responded**
- Capture **feedback that shaped its next step**, plus any **retries or human checkpoints**

> **GOOD LUCK**

---

## 8. Appendix — Three Examples for Reference (summaries)

> These are **illustrative only** — pick your own problem. Included in PDF pages 8–10.

### Example A — Code Analysis: Is this repository actually good?

- **01 Who:** Team considering purchase of a **private repository**; needs to know what the code is worth without having built it.
- **02 Bottleneck:** README/demo reveals little; buyer must sense quality across build, tests, architecture, dependencies, technical debt, PRs/issues, reviewer subjectivity — no repeatable, consistent method → valuation depends on incomplete judgment.
- **03 Does agent solve it well?** Agent analyzes repo and gives **clear quality assessment** before negotiation. Team defines "good" and valuation influence. Test: qualified reviewers rank **10 approved codebases** with shared rubric; give same codebases + rubric to agent and baseline — does agent get closer to reviewers and explain each position with evidence?
- **04 Reproducible?** Use approved repos; document setup, commands, tool versions, expected output for both; tie every score to file/test/build output; clean-environment rerun reproduces assessment & ranking.

### Example B — Candidate Evaluation: Should we hire this person?

- **01 Who:** **Recruiters & hiring managers** deciding fit; evidence spread across JD, target profile, CV, interview records, assessments.
- **02 Bottleneck:** Reviewing sources in isolation → miss contradictions / overweight one signal; candidate looks perfect despite misalignment; cheating suspicion makes it sensitive (warning ≠ proof).
- **03 Does agent solve it well?** Agent brings evidence into **one review**, connects requirements to demonstrated skills, checks experience against approved sources, explains discrepancies, surfaces evidence & uncertainty, **leaves final decision to qualified reviewer**.
- **04 Reproducible?** Use **approved/synthetic** cases (no private info); same cases for baseline + agent including one with **conflicting signals**; report all results incl. failures; trace each score/concern to source; second reviewer can reproduce without major discrepancies.

### Example C — Podcast Translation: Can every version still feel like the same show?

- **01 Who:** **Podcast creators/teams** responsible for how a show sounds in **every language** — translated episode must stay consistent with episodes before it.
- **02 Bottleneck:** Context spans **hours of audio, multiple speakers, earlier episodes, prior translation choices**. Episode OK in isolation → series drifts: name pronounced differently, recurring phrase translated inconsistently, joke loses meaning due to earlier reference handling. Each sentence correct, series incoherent.
- **03 Does agent solve it well?** Translate across **episodes & languages** while keeping **speaker identity, pronunciation, recurring terms, tone, prior decisions** consistent; whether transcript/subtitles/dubbed audio, preserve meaning & timing, sound natural.
- **04 Reproducible?** Define evaluation **before** running: fixed set of episodes + target languages, same inputs for baseline & agent, include one **recurring-detail dependent** case; each translation choice points to **source audio or approved material** (show notes/glossary); anyone can rerun and check.

---

*End of clean extraction. See raw text in `PROBLEM_RAW.txt` (pages 1–10). Execution directive (`docs/00-EXECUTION-DIRECTIVE.md`) governs how to act on this statement.*
