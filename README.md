# Frontier Engineering Challenge 2026 — micro1

> **Build at the frontier of agentic AI** · Aug 28–31, 2026 · Online, Individual, Free  
> Participant: **shashwatbajpai1729** · Kickoff: Aug 28 15:00 UTC (8:30 PM IST)

[![Status](https://img.shields.io/badge/status-pre--kickoff%20scaffold-active-yellow)](#stages--timeline)
[![Reproducibility](https://img.shields.io/badge/reproducibility-docker%20%2B%20make-blue)](#reproduction-guide)
[![Agents](https://img.shields.io/badge/agents-required%20%2B%20disclosed-purple)](#agent-trajectories)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

This repo is a **pre-kickoff scaffold** — fully structured so that the moment the problem PDF drops at kickoff, you paste it into `PROBLEM.md` and start building. Nothing is wasted: every folder maps to a submission-package requirement and every script is `make` -reproducible.

---

## Table of Contents

1. [Overview](#overview)
2. [Intended User & Value Proposition](#intended-user--value-proposition)
3. [Quick Start (Clean Machine in < 5 min)](#quick-start-clean-machine-in--5-min)
4. [Repository Structure](#repository-structure)
5. [Baseline vs Advanced](#baseline-vs-advanced)
6. [Reproduction Guide](#reproduction-guide)
7. [Evaluation Strategy](#evaluation-strategy)
8. [Agent Trajectories](#agent-trajectories)
9. [Improvement Changelog](#improvement-changelog)
10. [Submission Package Checklist](#submission-package-checklist)
11. [Stages & Timeline](#stages--timeline)
12. [Failure Mode & Hot Take](#failure-mode--hot-take)
13. [References](#references)

---

## Overview

**Challenge:** Use coding agents to solve a real-world software engineering problem where correctness, reproducibility, and human judgment matter. Judges score out of 100 after a strict qualification gate (eligibility → completeness → integrity → trace → reproducibility).

**Theme:** *Build at the frontier of agentic AI — where convincing is not enough.* Incomplete requirements, hidden dependencies, edge cases, failure modes, and decisions requiring technical judgment.

**Key constraint discovered from brief:** Every valid entry must present **both** a baseline solution and an advanced solution. Advanced must be a meaningful improvement in capability, reliability, efficiency, coverage, or engineering quality — not cosmetic.

> **Current state:** Problem statement NOT YET RELEASED. This README will be updated at `T+0h` kickoff with the real problem summary linked to `PROBLEM.md` and `docs/problem-brief.md`.

---

## Intended User & Value Proposition

*This section is intentionally templated pre-kickoff — fill at T+0 after reading the PDF. Judges explicitly ask for it in the README.*

| Slot | Pre-Kickoff Placeholder (replace at kickoff) |
|------|-----------------------------------------------|
| **Intended user** | _e.g., "Solo ops engineer triaging agent-generated PRs under time pressure"_ |
| **Current bottleneck** | _e.g., "Cannot trust agent output without manual edge-case audits; reproducibility breaks across machines"_ |
| **Why solving it is valuable** | _e.g., "Cuts review time 60%, prevents production regressions, makes agent work auditable"_ |
| **Success metric** | _e.g., "P95 task success > 90%, repro time < 3 min, 100% trajectory coverage"_ |

**Template sentence to complete at kickoff:**
> "This project is for **[user]** who today **[pain]** — we solve it by **[approach]** so they can **[outcome]**, measured by **[metric in /evidence/benchmarks/results.md]**."

---

## Quick Start (Clean Machine in < 5 min)

```bash
# 1. Clone & enter
git clone <your-repo-url> && cd micro1-front

# 2. One-command setup (python 3.11+, node 20+ OR docker)
make setup          # pip + npm + pre-commit hooks
# OR docker path
make docker-build && make docker-setup

# 3. Run baseline and advanced
make run-baseline   # → http://localhost:8000 (baseline) + logs in evidence/
make run-advanced   # → http://localhost:8001 (advanced)

# 4. Run all tests + evaluation harness
make test           # unit + integration + e2e
make eval           # produces evidence/benchmarks/results.json

# 5. Full reproducibility check (clean env simulation)
make reproduce      # scripts/reproduce.sh — judges run exactly this
```

See [**REPRODUCTION.md**](REPRODUCTION.md) for exact commands per path (venv, docker, conda) and expected outputs.

---

## Repository Structure

```
micro1-front/
├── README.md                 # This file — intro, user, changelog pointer
├── PROBLEM.md                # PASTE the full problem PDF text here at kickoff
├── REPRODUCTION.md           # Reproduction guide (clean-env steps, versions, runtime, cost)
├── ARCHITECTURE.md           # System design, decisions, trade-offs
├── CHANGELOG.md              # Improvement Changelog — every meaningful iteration + evidence
├── CONTRIBUTING.md           # How to work fast during the sprint
│
├── baseline/                 # Simple, correct, minimal solution (MUST exist)
│   ├── README.md
│   ├── src/                  # Python (FastAPI) OR TS (Express) — switch via baseline/Makefile
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml / package.json
│   └── run.sh
│
├── advanced/                 # Meaningful improvement (capability/reliability/efficiency)
│   ├── README.md
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml / package.json
│   └── run.sh
│
├── shared/                   # Code/data shared by both (e.g., schemas, fixtures)
│   ├── schemas/
│   ├── fixtures/
│   └── utils/
│
├── scripts/                  # All reproducible entrypoints
│   ├── setup.sh
│   ├── run_baseline.sh
│   ├── run_advanced.sh
│   ├── eval.sh
│   ├── eval.py
│   ├── reproduce.sh
│   └── capture_trajectory.sh
│
├── tests/                    # Cross-cutting tests (e2e, contract, load)
│   ├── e2e/
│   ├── integration/
│   └── load/
│
├── evidence/                 # Every claim → evidence here (judges love this)
│   ├── benchmarks/
│   │   ├── results.json
│   │   ├── results.md
│   │   └── comparison.md     # baseline vs advanced table (THE money slide)
│   ├── trajectories/         # Raw agent traces (JSON + markdown)
│   └── screenshots/
│
├── docs/
│   ├── problem-brief.md      # Your distilled problem + constraints + acceptance tests
│   ├── evaluation-criteria.md
│   ├── submission-checklist.md
│   ├── video-script.md       # 5-min video walkthrough script
│   ├── architecture-decisions.md  # ADRs
│   └── agent-instructions.md # The exact prompts you gave each agent
│
├── .agent/
│   ├── instructions/         # Agent instruction files (what shapes each agent)
│   └── trajectories/         # Symlink/mirror to evidence/trajectories for submission
│
├── docker-compose.yml
├── Makefile
├── .env.example
└── .gitignore
```

**Design principle:** Baseline and advanced are **fully independent** — judges can `cd baseline && make run` without touching advanced. `shared/` prevents duplication without coupling.

---

## Baseline vs Advanced

| Dimension | Baseline | Advanced (must beat baseline meaningfully) |
|-----------|----------|---------------------------------------------|
| **Goal** | Correct + minimal + understandable in < 1 day | Measurable win on ≥2 axes: capability, reliability, efficiency, coverage |
| **Examples of valid deltas** | Single-pass agent, no retries, happy-path only | Retry with verification, self-correction, edge-case handling, caching, eval harness, observability, safer sandboxing |
| **How we prove it** | `evidence/benchmarks/results.json` — baseline row | Same file — advanced row + `comparison.md` with p-values / % deltas |
| **Forbidden** | — | Cosmetic-only variation (same logic, different styling) |

> Pre-kickoff strategy: build baseline **first** (ship end of Day 1), then layer advanced features behind flags so you can always fall back to baseline for the qualification gate.

---

## Reproduction Guide

Full guide: **[REPRODUCTION.md](REPRODUCTION.md)** — written for someone starting from a clean Ubuntu 22.04 / macOS 14 / Windows 11 machine.

TL;DR for judges: `make reproduce` runs `scripts/reproduce.sh` which creates a fresh venv, installs pinned deps, runs baseline, advanced, and eval, and asserts outputs match `evidence/benchmarks/expected_outputs.json`.

Versions pinned at scaffold time: Python 3.11, Node 20, Docker 24+. Updated at kickoff if PDF prescribes a runtime.

---

## Evaluation Strategy

Scored **out of 100** after qualification gate. From the brief, tie-break order reveals 4 rubric pillars:

1. **Agent Solution & Engineering** — correctness, edge cases, failure modes, judgment
2. **Reproducibility** — can a stranger run it from README + scripts
3. **Measured Improvement** — advanced vs baseline with evidence
4. **End-to-End Quality** — docs, video, trajectory clarity, polish

See [docs/evaluation-criteria.md](docs/evaluation-criteria.md) for our mapping of each pillar to evidence artifacts.

Our strategy: **evidence over claims.** Every number in the README links to a file in `/evidence`.

---

## Agent Trajectories

Coding-agent use is **required**. You must disclose tools and submit representative trajectories: instruction → actions → tool responses → feedback → retries → human checkpoints → final result.

- Instructions that shaped each agent: [`docs/agent-instructions.md`](docs/agent-instructions.md) and [`.agent/instructions/`](.agent/instructions/)
- Raw traces: [`evidence/trajectories/`](evidence/trajectories/)
- Capture helper: `make capture-trajectory` → `scripts/capture_trajectory.sh`

We use **at least** one agentic workflow (OpenCode / Cursor / Claude Code / Codex). At kickoff we log every session to `evidence/trajectories/YYYY-MM-DD_<agent>_<task>.json`.

---

## Improvement Changelog

> Requirement: "Clearly labelled Improvement Changelog with an entry for every meaningful iteration, connected to the evidence that guided your next decision."

Full log: **[CHANGELOG.md](CHANGELOG.md)** — each entry links to the benchmark/observation that motivated it.

| # | Iteration | Evidence | Decision |
|---|-----------|----------|----------|
| 0 | Scaffold repo (pre-kickoff) | Challenge brief + FAQs | Created baseline/advanced split, repro harness, trajectory capture |
| 1 | _T+0: Paste problem PDF_ | `PROBLEM.md` | _Will fill at kickoff_ |

---

## Submission Package Checklist

Single source of truth: [docs/submission-checklist.md](docs/submission-checklist.md). Summary:

- [ ] Complete solution code + improvement changelog (`CHANGELOG.md`)
- [ ] Reproduction guide (`REPRODUCTION.md` + `make reproduce` green)
- [ ] Solution video ≤ 5 min (script in `docs/video-script.md`)
- [ ] Agent trajectories for every agent used (`evidence/trajectories/`)
- [ ] README with intended user, bottleneck, value, changelog pointer, failure mode, hot take
- [ ] Archive + tests + clean `make test` / `make eval`

---

## Stages & Timeline

| Stage | Window (Asia/Kolkata) | What we do |
|-------|----------------------|------------|
| **Prep** | Now – Aug 28 8:30 PM | Scaffold, rehearse `make reproduce`, draft agent instructions |
| **Kickoff** | Aug 28 8:30 PM IST / 15:00 UTC | Paste PDF → `PROBLEM.md` → distill to `docs/problem-brief.md` → baseline plan |
| **Build** | Aug 28–31 | Day 1: baseline green + tests; Day 2: advanced delta + eval; Day 3: polish, video, trajectories |
| **Submit** | By Aug 31 11:30 PM IST / 18:00 UTC | Final `make reproduce`, record video, zip, upload |

Registrations stay open after kickoff. Only the **latest complete submission** is evaluated.

---

## Failure Mode & Hot Take

*Required closing for README per submission package spec — templated until kickoff.*

- **Main failure mode:** _"If the starter repo prescribes a hidden dependency or rate-limited API, our current scaffold's happy-path eval will fail silently — mitigated by Day 1 contract tests and a sandboxed fallback in `advanced/src/fallback/`."_
- **Hot take:** _"Agentic AI wins not by generating more code, but by generating verifiable code — the team with the best eval harness, not the longest feature list, takes the prize."_

_Update both at T+6h after first baseline run._

---

## References

- Challenge: Frontier Engineering Challenge 2026 (micro1) — Aug 28–31, 2026
- Contact: Yeison Cruz — yeison@micro1.ai
- Socials: [LinkedIn](https://linkedin.com) · [Instagram](https://instagram.com) · [X](https://x.com) · [Reddit](https://reddit.com) · [YouTube](https://youtube.com)
- Tech policy: Python, TypeScript, Java, C++, Go, Rust (+ FastAPI/Flask/Django/LangGraph, Express/Nest/Next, Spring Boot, CMake, Go modules, Tokio/Axum/Actix — non-exhaustive)
- Prizes: $10k cash + 3 selective awards + up to 50 paid micro1 opportunities + $2–15/trace acquisition (cap $100–200, separate terms, not affecting judging)

---

**Next action at kickoff:** `make ingest-problem PROBLEM_PDF=path/to/pdf` (or paste text into `PROBLEM.md`) → `make brief` → start baseline.

*Built for `shashwatbajpai1729` — one line to walk away, full loop handled. See `CONTRIBUTING.md` for sprint workflow.*
