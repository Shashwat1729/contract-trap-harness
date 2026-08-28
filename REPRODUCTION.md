# Reproduction Guide

> Written for someone starting from a **clean environment** (Ubuntu 22.04 / macOS 14 / Windows 11 + WSL2). Every command is copy-pasteable and pinned. Judges run `make reproduce` — this doc explains what that does.

---

## 1. Prerequisites

| Requirement | Version | Check | Install |
|-------------|---------|-------|---------|
| Python | 3.11.x | `python --version` | https://python.org / `pyenv` |
| Node.js | 20.x LTS | `node --version` | https://nodejs.org / `nvm` |
| Docker | 24+ | `docker --version` | https://docs.docker.com/get-docker/ |
| Docker Compose | v2+ | `docker compose version` | bundled with Docker Desktop |
| Make | 4.x | `make --version` | `apt install make` / `brew install make` |
| Git | 2.40+ | `git --version` | https://git-scm.com |

**Optional but recommended:** `ffmpeg` (for video), `pdftotext` (for `make ingest-problem`).

All versions are **pinned** in `Makefile` and `docker-compose.yml`. If the problem PDF prescribes a different runtime at kickoff, this guide and `Makefile` will be updated and the delta logged in `CHANGELOG.md`.

---

## 2. Setup (Clean Environment)

### Path A — Native (fastest for development)

```bash
git clone <repo-url>
cd micro1-front

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
git clone <repo-url>
cd micro1-front
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
make test           # all: unit + integration + e2e
make test-unit      # pytest baseline/tests/unit advanced/tests/unit
make test-integration
make test-e2e       # tests/e2e — hits live services (run `make run-all` first)
make test-coverage  # coverage report → evidence/benchmarks/coverage.html
```

Expected: `X passed in Ys` (counts filled after kickoff). CI fails if coverage < configured threshold (pre-kickoff threshold: 70% — adjust per PDF).

---

## 5. Evaluation Harness

The harness is what proves **measured improvement** — the core judging criterion for "advanced vs baseline."

```bash
make eval
# Runs: python scripts/eval.py --baseline http://localhost:8000 --advanced http://localhost:8001
# Outputs:
#   evidence/benchmarks/results.json   # machine-readable
#   evidence/benchmarks/results.md     # human table
#   evidence/benchmarks/comparison.md  # the "money slide" — % deltas + p-values
```

**Metrics template (replace with real metrics at kickoff):**

| Metric | Baseline | Advanced | Delta |
|--------|----------|----------|-------|
| Success rate | _TBD_ | _TBD_ | _TBD_ |
| P95 latency | _TBD_ | _TBD_ | _TBD_ |
| Edge-case pass | _TBD_ | _TBD_ | _TBD_ |
| Cost / 1k tasks | _TBD_ | _TBD_ | _TBD_ |

Direct `make eval` output is committed to `evidence/benchmarks/results.json` — judges re-run and diff.

Data required: listed in `shared/fixtures/README.md` + `REPRODUCTION.md` §6. Public/synthetic data only unless PDF says otherwise.

---

## 6. Full Reproducibility Check (What Judges Run)

```bash
make reproduce
# → scripts/reproduce.sh
# Steps:
#   1. fresh venv (or --docker flag uses fresh containers)
#   2. make setup
#   3. make test          (assert green)
#   4. make run-all & wait for health
#   5. make eval          (assert results.json matches evidence/benchmarks/expected_outputs.json within tolerance)
#   6. teardown
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
| `make setup` | 2–4 min | $0 | pip + npm |
| `make test` | 30–90s | $0 | without LLM calls |
| `make eval` (with LLM) | 2–10 min | $0.10–2.00 | depends on problem; mock mode `EVAL_MOCK=1 make eval` costs $0 |
| `make reproduce` | 5–15 min | same | includes eval |
| Docker build (cold) | 3–6 min | $0 | cached <30s |

LLM costs are from **your own keys** in `.env` — never committed. `EVAL_MOCK=1` lets judges verify harness without keys.

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
git clone <url> && cd micro1-front
cp .env.example .env   # add keys only if you want real LLM eval; mock works without
make reproduce
# Check evidence/benchmarks/results.json and comparison.md
```

If anything fails, open an issue or contact: yeison@micro1.ai + repo owner.

---

*Last updated: pre-kickoff scaffold — Aug 28, 2026. Updated at kickoff if PDF prescribes env.*
