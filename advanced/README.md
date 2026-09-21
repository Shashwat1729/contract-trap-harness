# Advanced — verification-gated contract harness

The real system. Extracts clause spans for 12 playbook rules, matches them against
a risk playbook with precedent retrieval, and only surfaces a proposed redline
after it passes a deterministic dual-threshold evidence gate plus an optional live
LLM cross-check. Nothing auto-commits: every approved finding is a candidate for
human review with its `{contract_span, page:line, playbook_rule}` citation.

- **Endpoint:** FastAPI on `:8001` — `GET /health`, `POST /api/redline`,
  `GET /api/harness/stream` (SSE progress), `POST /api/harness/resume`
- **Measured:** 42.2% recall / 92.7% precision on 510 real CUAD contracts vs
  baseline's 15.5% / 53.7% (`evidence/benchmarks/comparison.md`).
- **Agentic mode (opt-in):** `advanced/src/harness/graph.py` runs the same pipeline
  as a LangGraph `StateGraph` (extract → risk → evidence → verify → revise →
  human_review) with checkpointing and a real `interrupt()` pause.
  Enable with `ENABLE_LANGGRAPH=1`; the direct pipeline is the certified default.

## Run

```bash
make run-advanced
# or isolated
cd advanced && python -m src.main --port 8001
curl http://localhost:8001/health  # → {variant:"advanced", features:[...]}
```

## Test

```bash
python -m pytest advanced/tests/unit advanced/tests/integration -v   # 83 passed, 1 skipped
```

## Structure

```
advanced/
├── src/
│   ├── main.py        # FastAPI app (+ SSE stream, resume, memory endpoints)
│   ├── config.py      # env flags (all documented in .env.example)
│   ├── core.py        # verification-gated pipeline + process_contract_graph()
│   ├── fallback/      # sandboxed graceful degradation (Rule: no auto-commit)
│   └── harness/
│       ├── ingest.py    # PDF/DOCX → paginated text with provenance
│       ├── extract.py   # 41 CUAD types → 12 SaaS rules (regex + WORD_NUM)
│       ├── risk.py      # 12-rule playbook + precedent retrieval + self-reflective RAG
│       ├── verify.py    # dual-threshold evidence gate (PASS/REJECT + revise hint)
│       ├── llm_verify.py# live LLM cross-check (key required, mock-degrades)
│       ├── llm_extract.py # LLM-as-generator for zero-hit clause types (opt-in)
│       ├── semantic.py  # hosted-embedding layer (opt-in, preliminary)
│       ├── bm25.py      # $0 lexical layer (opt-in, 510-contract validated)
│       ├── memory.py    # structured negotiation memory + tier-aware routing
│       ├── router.py    # field-level routing to human review
│       ├── report.py    # .docx redline generation
│       ├── graph.py     # LangGraph StateGraph (opt-in agentic mode)
│       ├── keys.py      # multi-key fallback pool
│       ├── llm.py       # provider-agnostic LLM client (litellm)
│       └── embed.py     # embedding client
├── tests/
│   ├── unit/          # core, fallback, generalization, stress, semantic, LLM, graph, BM25
│   └── integration/   # API contract tests
├── pyproject.toml     # pytest + coverage (fail-under 80) + mypy strict
├── requirements.txt   # pinned
├── Dockerfile
└── run.sh
```

## Feature flags (all in `.env.example`, all default-safe)

| Flag | Default | Effect |
|---|---|---|
| `EVAL_MOCK=1` | on | fully offline, deterministic, $0 |
| `ENABLE_LLM_VERIFY` | on | LLM cross-check when a key exists |
| `ENABLE_BM25_EXTRACTION` | off | +3.9pp recall, opt-in trade-off |
| `ENABLE_SEMANTIC_EXTRACTION` | off | preliminary, opt-in |
| `ENABLE_LLM_EXTRACT` | off | LLM proposes zero-hit candidates |
| `ENABLE_LANGGRAPH` | off | StateGraph engine instead of direct |
| `ENABLE_GRAPH_INTERRUPT` | off | real pause-for-review |
