# Baseline — Simple, Correct, Minimal

> **Purpose:** Qualification gate. Must be correct, reproducible, and pass acceptance tests alone. No cleverness — just happy path done right. Judges can run this in isolation.

## What "baseline" means for this challenge

- Solves the core problem with a single approach (one-pass, no retries, no unverified claims)
- Handles happy path + basic validation; edge cases may return honest errors (not hallucinations)
- No speculative features — if the PDF doesn't say to do it, baseline doesn't
- Must be **fully independent** — `cd baseline && make run` works without `advanced/` or `shared/` beyond schemas

## Run

```bash
# from repo root
make run-baseline
# or directly
./scripts/run_baseline.sh
# or isolated
cd baseline && python -m src.main --port 8000
# health check
curl http://localhost:8000/health
curl http://localhost:8000/api/example  # replace with real endpoint at kickoff
```

## Test

```bash
make test-unit        # or: cd baseline && pytest tests/unit -v
make test-integration # or: cd baseline && pytest tests/integration -v
pytest --cov=src --cov-report=term-missing
```

## Structure

```
baseline/
├── src/
│   ├── main.py        # FastAPI app factory + entrypoint
│   ├── config.py      # env loading, no secrets committed
│   ├── routes.py      # API routes (replace at kickoff)
│   └── core.py        # domain logic — keep this pure/testable
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── run.sh
```

## What to build on Day 1

1. Paste problem → define routes/schemas in `shared/schemas/`
2. Implement `src/core.py` — pure functions, easy to test
3. Wire `src/routes.py` + `src/main.py`
4. Contract tests against acceptance tests
5. `make test && make eval` — record evidence

## Non-goals

- Retries, caching, self-correction (that's advanced)
- UI polish (unless problem is UI)
- Anything that needs a claim without evidence
