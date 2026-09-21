# Reproduction Guide

> Written for someone starting from a **clean environment** (Ubuntu 22.04 / macOS 14 / Windows 11 + WSL2). Every command is copy-pasteable and pinned. Judges run `make reproduce` — this doc explains what that does.

---

## 1. Prerequisites

| Requirement | Version | Check | Install |
|-------------|---------|-------|---------|
| Python | 3.11.x | `python --version` | https://python.org / `pyenv` |
| Docker | 24+ (optional) | `docker --version` | https://docs.docker.com/get-docker/ |
| Docker Compose | v2+ | `docker compose version` | bundled with Docker Desktop |
| Make | 4.x | `make --version` | `apt install make` / `brew install make` |
| Git | 2.40+ | `git --version` | https://git-scm.com |

**Optional but recommended:** `ffmpeg` (for video), `pdftotext` (for `make ingest-problem`).

All versions are **pinned** in `baseline/requirements.txt`, `advanced/requirements.txt`,
`app/requirements.txt`, and `docker-compose.yml`.

---

## 2. Setup (Clean Environment)

### Path A — Native (fastest for development)

```bash
git clone https://github.com/Shashwat1729/contract-trap-harness.git
cd contract-trap-harness

# Creates venv, installs pinned deps for root + baseline + advanced, installs hooks
make setup
# Equivalent manual steps:
#   python -m venv .venv && source .venv/bin/activate
#   pip install -r requirements.txt
#   pip install -r baseline/requirements.txt
#   pip install -r advanced/requirements.txt
#   npm install   # if TypeScript paths present
#   pre-commit install  # optional

cp .env.example .env
# Edit .env if the problem requires API keys (keys stay OUT of the submission zip)
```

Expected output: `Setup complete. Run 'make test' to verify.`

### Path B — Docker (most reproducible, what CI/judges prefer)

```bash
git clone https://github.com/Shashwat1729/contract-trap-harness.git
cd contract-trap-harness
cp .env.example .env

make docker-build
make docker-setup
# Or one shot:
docker compose up --build -d
docker compose exec app make test
```

Approximate runtime: setup 2–4 min (native) / 3–6 min (docker build, cached layers < 30s).

Approximate cost: $0 local; if problem requires LLM APIs, see §6 Cost.

---

## 3. Running the Solutions

### Baseline (simple, correct, minimal)

```bash
make run-baseline
# → baseline on http://localhost:8000
# → logs to evidence/benchmarks/baseline_run.log

# Manual:
#   ./scripts/run_baseline.sh
#   cd baseline && python -m src.main --port 8000
```

**What to expect:** Baseline serves the core task only (happy path), no retries/caching. Check `http://localhost:8000/health` → `{"status":"ok","variant":"baseline"}`.

### Advanced (meaningful improvement)

```bash
make run-advanced
# → advanced on http://localhost:8001
# → logs to evidence/benchmarks/advanced_run.log

# Manual:
#   ./scripts/run_advanced.sh
#   cd advanced && python -m src.main --port 8001
```

**What to expect:** Advanced serves same API + additional capabilities (verification, self-correction, caching, better error handling — specifics filled at kickoff). Health: `http://localhost:8001/health` → `{"status":"ok","variant":"advanced","features":[...]}`.

### Both at once

```bash
make run-all        # both services via docker-compose
# or
make docker-up      # docker compose up -d baseline advanced
```

---

## 4. Tests

```bash
make test           # unit + integration + dashboard smoke + e2e (all offline)
make test-e2e       # tests/e2e — in-process via TestClient, no live services needed
make test-coverage  # coverage report (fail-under 80)
make mypy           # strict type check
```

Expected: baseline 9 passed, advanced 83 passed / 1 skipped, dashboard 5 passed,
e2e 3 passed. Coverage gate: 80 (`make test-coverage`).

---

## 5. Evaluation Harness

The harness is what proves **measured improvement** — the core judging criterion for "advanced vs baseline."

```bash
make eval          # EVAL_MOCK not set — runs the real LLM cross-check/judge if an API key is present
make eval-mock     # EVAL_MOCK=1 — fully offline, deterministic, no API key needed
# Runs: python scripts/eval_harness.py (no args — reads shared/fixtures/contracts/ directly,
#       runs both baseline.process_contract and advanced.process_contract_advanced in-process)
# Outputs:
#   evidence/benchmarks/results.json   # machine-readable
#   evidence/benchmarks/comparison.md  # the "money slide" — every number computed live, no hardcoded targets
```

**Real metrics (see `evidence/benchmarks/comparison.md` for full tables):**

Primary — clause presence on 510 real CUAD contracts:

| Metric | Baseline | Advanced | Delta |
|--------|----------|----------|-------|
| Recall | 15.5% | 42.2% | +26.7pp |
| Precision | 53.7% | 92.7% | +39.0pp |

Secondary — 30-contract trap suite (same cases for both):

| Metric | Baseline | Advanced | Delta |
|--------|----------|----------|-------|
| Trap recall | 56% | 100% | +44pp |
| Evidence-supported edits | 21.4% | 83.7% | +62.3pp |
| Unsupported edits | 78.6% | 16.3% | -62.3pp |
| Est. review time/contract | 5.1 min | 3.4 min | -1.7 min |

Trap Recall is deterministic and needs no API key. The optional LLM Judge secondary metric (`scripts/llm_judge.py`, 5-dimension rubric) degrades to a clearly-labeled mock score with no key — see `evidence/benchmarks/llm_judge_results.json` for its current `mode`.

`make eval` output is committed to `evidence/benchmarks/results.json` — judges re-run and diff.

Data required: listed in `shared/fixtures/README.md` + `REPRODUCTION.md` §6. Public/synthetic data only unless PDF says otherwise.

---

## 6. Full Reproducibility Check (What Judges Run)

```bash
make reproduce
# → scripts/reproduce.sh (actual steps, verified against the real script, not aspirational):
#   1. bash scripts/setup.sh   (fresh .venv, installs baseline + advanced + dashboard requirements.txt)
#   2. baseline test suite (pytest, no network)
#   3. advanced unit + integration test suite (pytest, no network)
#   4. dashboard smoke suite (streamlit.testing.v1.AppTest -- actually runs app/streamlit_app.py, EVAL_MOCK=1)
#   5. held-out generalization suite (15 fresh contracts, EVAL_MOCK=1)
#   6. stress suite (7 messy real-world fixtures, EVAL_MOCK=1)
#   7. PRIMARY metric: CUAD ground-truth eval, 510 real contracts (no key needed -- regex-only default)
#   8. 30-fixture eval harness (EVAL_MOCK=1) -> evidence/benchmarks/results.json + comparison.md
#   9. asserts results.json and comparison.md exist and are non-empty
```

Exit code `0` = reproducible. Output is `evidence/benchmarks/reproduce.log`.

### Versions recorded at last `make reproduce`:

```
Python: 3.11.x (pinned in .python-version)
Node:   20.x
pip:    24.x
Docker: 24.x
OS:     $(uname -a) logged to reproduce.log
```

If PDF pins a runtime (e.g., "Python 3.10 only, no network"), that overrides this file and is noted in `CHANGELOG.md`.

---

## 7. Cost & Runtime Estimates

| Task | Time | Cost | Notes |
|------|------|------|-------|
| `make setup` | 2-4 min | $0 | pip + npm |
| `make test` | 30-90s | $0 | without LLM calls |
| `make eval` (mock, offline) | 1-2 min | $0 | deterministic, 30 contracts, EVAL_MOCK=1 |
| `make eval` (with LLM verify) | 2-10 min | $0.10-2.00 | depends on provider; EVAL_MOCK=1 costs $0 |
| `make reproduce` | 5-15 min | $0-2 | includes eval |
| Docker build (cold) | 3-6 min | $0 | cached <30s |

Per-model cost breakdown (30 contracts, real LLM calls, 2026 pricing approx):

| Model (LLM_MODEL) | Provider | Cost per 30 contracts | Cost per contract | Notes |
|---|---|---|---|---|
| gemini/gemini-2.5-flash | Google AI Studio | ~$0.02-0.05 | ~$0.001 | default, free tier 20 req/day |
| gpt-4o-mini | OpenAI | ~$0.08-0.12 | ~$0.003 | 1M input tokens ~ $0.15 |
| claude-haiku-4-5 | Anthropic | ~$0.10-0.15 | ~$0.004 | similar |
| EVAL_MOCK=1 | none | $0 | $0 | deterministic gate only |

Embedding cost (semantic layer, optional):

| Model | Cost per 510 CUAD contracts |
|---|---|
| gemini-embedding-001 | ~$0.02-0.04 | free tier quotas (see CHANGELOG #13) |

Budget reproducibility: `EVAL_MOCK=1 make eval` is always $0 and is what CI/judges without keys run.

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port already in use 8000/8001` | `make kill` or `lsof -i :8000` then kill |
| `ModuleNotFoundError` | `make setup` again; check `python --version` is 3.11 |
| `docker compose` not found | `docker-compose` (hyphen) fallback: `make docker-up-legacy` |
| Eval needs API key | `cp .env.example .env` and add key, or `EVAL_MOCK=1 make eval` |
| Windows path issues | Use WSL2 or `make docker-*` paths |

---

## 9. For Evaluators / Judges

Minimum to verify:

```bash
git clone https://github.com/Shashwat1729/contract-trap-harness.git && cd contract-trap-harness
cp .env.example .env   # add keys only if you want real LLM eval; mock works without
make reproduce
# Check evidence/benchmarks/results.json and comparison.md
```

If anything fails, please open a GitHub issue with your OS, Python version, and the
relevant section of `evidence/benchmarks/reproduce.log`.

---

*Last verified: Aug 2026 via `make reproduce` (see `evidence/benchmarks/reproduce.log`).*
