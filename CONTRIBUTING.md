# Contributing to Contract Trap Harness

Thanks for your interest! This guide covers how to set up, test, and submit changes.

## Setup

```bash
git clone https://github.com/Shashwat1729/contract-trap-harness.git
cd contract-trap-harness
make setup          # creates .venv, installs baseline + advanced + dashboard deps
cp .env.example .env
```

No API key is needed: `EVAL_MOCK=1` (the default in `.env.example`) gives a full,
deterministic, $0 run. Add a real `GEMINI_API_KEY` / `OPENAI_API_KEY` only if you
want to exercise the live LLM cross-check paths.

## Workflow

1. **Branch from `master`:** `git checkout -b feat/<short-description>`
2. **Keep `master` green:** `make reproduce` must pass before every merge.
3. **Small, atomic commits** (conventional commits):
   `feat(baseline): ...`, `fix(advanced): ...`, `docs: ...`, `eval(harness): ...`
4. **Tests alongside code** — never after. Coverage gate: 80% (`make test-coverage`).

## Verification commands

| Command | What it does |
|---|---|
| `make test` | baseline + advanced + dashboard smoke + e2e (offline, no keys) |
| `make test-coverage` | same with coverage report (fail-under 80) |
| `make mypy` | strict type check on `advanced/src`, lenient on `baseline/src` |
| `make eval` | 30-contract trap suite → `evidence/benchmarks/` |
| `make eval-cuad-ground-truth` | primary metric: 510 real CUAD contracts (auto-downloads dataset once) |
| `make reproduce` | full clean-room check — what reviewers run |

## Ground rules

- **Every claim needs evidence.** Numbers in docs/PRs must link to a file under `evidence/benchmarks/`.
- **No secrets in git.** Keys live in `.env` only (gitignored). `make pre-submit` scans for staged secrets.
- **No synthetic-looking wins.** New fixtures go in `shared/fixtures/` with a documented source; self-graded suites must be labeled as such.
- **Deterministic by default.** Anything requiring network/keys must degrade gracefully under `EVAL_MOCK=1`.

## Project layout

- `baseline/` — single-pass reference detector (FastAPI :8000)
- `advanced/` — verification-gated harness (FastAPI :8001)
- `shared/` — schemas + fixtures shared by both
- `app/` — Streamlit monitoring dashboard
- `scripts/` — reproducible entry points (`eval_*`, `reproduce.sh`, `setup.sh`)
- `evidence/` — committed benchmark outputs (the project's memory)
- `docs/` — background + design docs (`docs/archive/` holds hackathon-process notes)

See `ARCHITECTURE.md` for design decisions and trade-offs.
