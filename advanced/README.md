# Advanced — Meaningful Improvement over Baseline

> **Purpose:** Win on ≥2 axes: capability, reliability, efficiency, coverage, or engineering quality. Must be a *real* delta — cosmetic variation is disqualification per brief.

## Valid deltas (pick ≥2, prove with evidence)

| Axis | Example | How to prove |
|------|---------|--------------|
| **Capability** | Handles edge cases baseline doesn't (e.g., malformed input, multi-step) | `evidence/benchmarks/comparison.md` edge_pass delta |
| **Reliability** | Retry with verification, fallback, graceful degradation | failure-rate drop, chaos tests |
| **Efficiency** | Caching, batching, streaming, cheaper model routing | p95 latency, cost/1k ↓ |
| **Coverage** | More acceptance tests passing | pass rate ↑ |
| **Engineering quality** | Observability, eval harness, contract tests, typed schemas | coverage, repro time |

## Run

```bash
make run-advanced
# or
./scripts/run_advanced.sh
# or isolated
cd advanced && python -m src.main --port 8001
curl http://localhost:8001/health  # → {variant:"advanced", features:[...]}
```

## Test

```bash
cd advanced && pytest tests/ -v --cov=src
make test-e2e  # cross-cutting
```

## Structure

```
advanced/
├── src/
│   ├── main.py        # mirrors baseline API + extensions
│   ├── config.py
│   ├── routes.py
│   ├── core.py        # may import baseline core and wrap it
│   ├── fallback/      # sandbox / safe fallback for rate-limited / hidden deps
│   │   └── handler.py
│   ├── verify.py      # verification / self-correction layer
│   └── cache.py       # optional efficiency layer
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── requirements.txt
├── Dockerfile
└── run.sh
```

## Strategy

- **Start from baseline:** copy baseline core, then layer improvements behind flags so you can always fall back.
- **One iteration at a time:** each iteration = one entry in `CHANGELOG.md` with evidence link.
- **Keep the money slide updated:** `evidence/benchmarks/comparison.md` is the first thing judges read after the video.

## Anti-patterns (will lose points)

- Same logic, different styling → "cosmetic variation" = disqualification risk
- Claims without `evidence/` link
- Non-reproducible deps or hidden state
