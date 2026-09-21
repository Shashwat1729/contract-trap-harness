# Baseline — single-pass reference detector

The comparison point for every number in this repo. A deterministic,
single-pass clause-trap detector with no verification gating, no retries, and
no memory: regex + keyword rules over paginated contract text.

- **Endpoint:** FastAPI on `:8000` — `GET /health`, `POST /api/redline`
- **Fair by design:** receives the exact same contracts and the exact same
  scoring as `advanced/` (see `scripts/eval_harness.py`).
- **Measured:** 15.5% recall / 53.7% precision on 510 real CUAD contracts
  (`evidence/benchmarks/comparison.md`).

## Run

```bash
# from repo root
make run-baseline
# or isolated
cd baseline && python -m src.main --port 8000
# health check
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/redline \
  -H 'Content-Type: application/json' \
  -d '{"contract_text": "<full text>", "contract_id": "msa_01"}'
```

## Test

```bash
cd baseline && pytest tests -v   # 9 passed
```

## Structure

```
baseline/
├── src/
│   ├── main.py     # FastAPI app + /api/redline
│   ├── config.py   # env loading, no secrets committed
│   └── core.py     # pure detection logic (PLAYBOOK + cross-trap checks)
├── tests/
│   ├── unit/         # core detection tests
│   └── integration/  # API contract tests
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── run.sh
```

## Non-goals (by design — this is what `advanced/` adds)

- Verification gating, retries, self-correction
- Precedent retrieval, memory, human-in-the-loop
