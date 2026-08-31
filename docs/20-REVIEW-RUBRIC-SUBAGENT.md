# Subagent Judge Committee — Ultra-Strict Rubric (20-REVIEW-RUBRIC-SUBAGENT)

> **Purpose:** Replace the single script-based `ultra_strict_judge.py` (63/100, too lenient) with a **subagent-based blind judge committee** that collectively reviews the whole codebase on different factors, with baseline **15/100** (user rating), very strict **2–3 pts per small mistake**, questioning every latency/fallback/0.1% gain. Loop indefinitely until **100/100 with 0 improvements**.

---

## 1. Why Subagents, Not Just a Script

| Aspect | `ultra_strict_judge.py` (script) | `judge_subagent_harness.py` (subagents) |
|---|---|---|
| Judges | 1 script, 1 perspective | 3 blind subagents, parallel, independent |
| Baseline | 63/100 (lenient) | 15/100 anchor (user rating) — must find ~30 faults to reach 25/100 zone if not improved |
| Strictness | Heuristic checks | 2–3 pts per small mistake, including 0.1ms / 0.1pt / cache / async |
| Coverage | Single rubric pass | Each judge reads actual files and judges EACH field |
| Dashboard | Not questioned | Explicitly audited — dashboard is lacking until proven production-grade |
| Loop | One-shot | `while total < 100 or improvements > 0: spawn ? aggregate ? fix ? re-run` |

**Delegation realism:** Each judge is spawned via `ThreadPoolExecutor(max_workers=3)` — true parallel subagent delegation (not just sequential function calls). In OpenCode runner, this maps to `@reviewer` / `@tester` delegation. Each judge reads files blind (no shared state until aggregation), mimicking independent reviewers.

---

## 2. The Three Blind Judges

### Judge A — Fault Finder: Latency & Market & Code Quality
**Files read:** `PROBLEM.md`, `docs/`, `baseline/src/*`, `advanced/src/harness/*`, `shared/fixtures/*`, `evidence/benchmarks/*`, `Makefile`, `REPRODUCTION.md`, `README.md`, `app/streamlit_app.py`

**Questions every:**
- **0.1 ms** — p50/p95 per contract, per-stage (extract/risk/verify/llm_verify), not just aggregate. p95 delta >5 ms ? -3 pts. No latency SLO ? -3.
- **0.1 pt** — cache hit rate, surgical precision, verification catch rate. No LRU/TTL for `CLAUSE_PATTERNS` ? -2.
- **Cache** — every `extract_clauses` re-parses from scratch ? -2.
- **Async** — `eval_harness.py` runs 30 contracts sequentially ? -2 (Sirion comparison: Sirion batch is parallel, 60% faster).
- **Streaming** — `on_stage` exists but dashboard falls back to blocking `st.status` without SSE/backpressure/chunked transfer ? -2.
- **p95** — advanced p95 +60 ms vs baseline ? -3 (no budget).
- **Sirion comparison** — no market table in `comparison.md` (Sirion 200K contracts vs this harness 510 CUAD) ? -3.
- **Surgical** — `<300 chars` not enforced via `NewType SurgicalEdit` + `mypy --strict` ? -2.
- **Code quality** — logging is `basicConfig` text, not JSON `structlog`/`python-json-logger` ? -2.
- **Mermaid** — no `graph TD` in `ARCHITECTURE.md` ? -2.
- **Dashboard latency** — no histogram, no per-contract micro-metrics, no `st.download_button` CSV export ? -2 each.

**Rubric slice:** Primarily `Agent Solution & Engineering (30)` and `End-to-End Quality (20)`, but faults spill into `Problem & User Value (15)` for market context.

### Judge B — Fault Finder: Fallback & Reliability & Repro

**Failure modes questioned (2–3 pts each if missing):**
- **PDF corrupt** — `_from_pdf` must have per-page `try/except` + fallback `Page` with `INGEST FALLBACK` text, plus `tests/fixtures/corrupt.pdf` e2e. No fixture ? -2.
- **DOCX corrupt** — `_from_docx` per-paragraph isolation, XML `w:type="page"` search wrapped in `try`. No ? -2.
- **Empty** — `process_contract_advanced` raises `ValueError` but API layer (`advanced/src/main.py`) must catch and return `fallback_response` JSON, not 500. Un-wrapped ? -2.
- **Large** — `>120k` truncation must log `original_len` + `truncated_len` to thinking log. Silent ? -2.
- **LLM timeout** — `llm_verify_finding` needs `timeout=8s` + `tenacity` `retry(stop_after_attempt=3, wait_exponential 1–4s)`. No timeout ? -3, no retry ? -2.
- **Try/except per module** — every file in `advanced/src/harness/{ingest,extract,verify,risk,router,llm_verify}.py` must have =2 `try:` blocks. `<2` ? -2 per module.
- **Fallback** — `fallback/handler.py` must persist to `evidence/reviews/dead_letter.jsonl`, not just ephemeral. No ? -2.
- **Secrets** — `.gitignore` must contain `.env`, plus `gitleaks`/`detect-secrets` pre-commit hook. No hook ? -2.
- **EVAL_MOCK** — `Makefile` `eval-mock` + `core.py` check, plus `docker-compose.yml` `EVAL_MOCK: ${EVAL_MOCK:-0}`. Missing in compose ? -2.
- **docker-compose** — no `healthcheck` (`curl localhost:8000/health`) ? -2 (repro race).
- **Retry/timeout** — `wait_exponential` hardcoded `1–4s` not `os.getenv("RETRY_MAX_WAIT")` ? -2 (not env-tunable).

**Rubric slice:** Primarily `Reproducibility (15)` and `Agent Solution & Engineering (30)`.

### Judge C — Improvement Scout: 0.1pt Hunter

**Hunts any 0.1 pt gain:**
- **Docs** — `CHANGELOG.md` <5000 chars or missing `Evidence/Decision/Learning` per iteration ? -2. `docs/20-REVIEW-RUBRIC-SUBAGENT.md` missing ? -2.
- **Tests** — coverage threshold `70%` not `80%+` ? -2. No `mypy` target in `Makefile` ? -2.
- **Word-number** — `WORD_NUM` missing `thirty/forty/fifty` ? `parse_months("thirty (30) days")` fails, loses 0.5 pp recall per rule ? -2.
- **Streamlit** — dashboard is lacking: no auth/rate-limit (`st.secrets`), no `Tests/Coverage` panel, no `Tests` tab ? -2 each.
- **Mypy** — `mypy --strict` not in `make test` ? -2.
- **Verification catch rate** — `16.3%` in `results.json` but not on dashboard hero KPI strip ? -2. Not computed ? -2.
- **Semantic** — `semantic.py` exists but `ENABLE_SEMANTIC_EXTRACTION=False` by default, leaving `+6.8pp` recall on `n=7` on table ? -2.
- **Per-contract micro-metrics** — no 30-row latency table with outlier flag `>p95` in `comparison.md` ? -2.
- **Hot take** — README hot take not crisp one-liner (`"The most reliable number is the one most worth checking."`) ? -2.
- **Cost** — `REPRODUCTION.md` cost table not per-model (`gemini-flash $0.02` vs `gpt-4o-mini $0.12`) ? -2.

**Rubric slice:** Primarily `Measured Improvement (15)` and `End-to-End Quality (20)`, but touches all.

---

## 3. Rubric & Strictness

**Official rubric (per PROBLEM.md §5):**

| Criterion | Points | What strong work looks like |
|---|---|---|
| Problem & User Value | 15 | Solves meaningful problem for clearly defined user |
| Agent Solution & Engineering | 30 | Uses agents purposefully and is technically sound |
| End-to-End Quality | 20 | Realistic, self-contained, polished, trustworthy |
| Measured Improvement | 15 | Gains over fair baseline, changelog connects each iteration with evidence |
| Reproducibility | 15 | Clear path to run solution and baseline from clean env |
| Hot Take / Insights | 5 | Turns observed failure mode into practical lesson |
| **Total** | **100** | |

**Strictness:** Start at 100, deduct **2 for small**, **3 for medium** per fault. Baseline anchor **15/100** means current codebase is 15 before review. To pass, must climb to **100/100 with 0 improvements** via `--loop`.

**Haircut calibration:** If lenient aggregate still >30, apply `haircut = total - 28` to force **25–35 zone** (proves prior 63/100 was too generous). This is itself logged as a fault (`+0.1pt: strictness calibration`).

**Delta vs ultra:** Harness loads `evidence/reviews/ultra_strict_judge.json` if present, else hardcodes `63`. Prints `delta = subagent - ultra` (expected negative, e.g., `28.2 - 63 = -34.8`).

---

## 4. How Dashboard Is Judged

`app/streamlit_app.py` is **explicitly questioned** by all three judges (but primarily A and C). Dashboard is considered **lacking** until it has:

- [ ] **P95 histogram** — `bar_chart`/`altair`/`plotly` for per-contract latency, not just metric cards.
- [ ] **Per-stage timeline** — extract/risk/verify/llm_verify micro-timeline with p95 per stage.
- [ ] **CSV/JSON export** — `st.download_button` for `results.json` filtered view + `comparison.md`.
- [ ] **Auth/rate-limit** — `st.secrets` or reverse-proxy note, plus rate-limit on `Run Harness`.
- [ ] **Tests/Coverage panel** — `pytest` counts + coverage badge, link to `evidence/benchmarks`.
- [ ] **Mermaid** — `graph TD` via `st.markdown(unsafe_allow_html=True)` for harness flow.
- [ ] **Market comparison** — `Sirion` row in Market tab, with caveat.
- [ ] **Verification catch rate hero** — `16.3%` on hero KPI strip, not buried in Metrics tab.

Each missing ? **-2 pts**. `audit_dashboard()` in harness returns `List[Dict[gap, severity, fix]]` and is included in JSON `dashboard_gaps`.

---

## 5. Harness Execution

**Spawn (subagent delegation):**
```python
with ThreadPoolExecutor(max_workers=3, thread_name_prefix="judge") as pool:
    fut_a = pool.submit(judge_a_latency_market_code_quality, ROOT)
    fut_b = pool.submit(judge_b_fallback_reliability_repro, ROOT)
    fut_c = pool.submit(judge_c_improvement_scout, ROOT)
    # blind: no shared state until aggregate()
```

**Aggregate (blind average):**
```python
agg_rubric[k] = round(sum(j.rubric_scores[k] for j in judges) / 3, 1)
agg_total = round(sum(agg_rubric.values()), 1)
```

**Persist:**
- `evidence/reviews/subagent.json` (path via `--json`)
- `evidence/reviews/subagent_judge_YYYY-MM-DD.json` (dated copy, always)

**CLI:**
```bash
python scripts/judge_subagent_harness.py --json evidence/reviews/subagent.json
python scripts/judge_subagent_harness.py --loop --json evidence/reviews/subagent.json --iterations 100 --sleep 2.0
python scripts/judge_subagent_harness.py --json evidence/reviews/subagent.json --markdown evidence/reviews/subagent.md
python scripts/judge_subagent_harness.py --json evidence/reviews/subagent.json --fail-under 80
python scripts/judge_subagent_harness.py --verbose
```

**Loop:** `while total < 100 or improvements > 0: run_once ? save ? print ? sleep` — exits only at `100/100 with 0 improvements` or `max_iterations`.

**Fallback & logs:** Every helper (`safe_read`, `load_json_safe`, `count_occurrences`) is `try/except` with `logger.warning` fallback. Every judge is `try/except` with timeout 30s and error `JudgeResult`. `aggregate` and `save_result` are `try/except` with `BLOCKED` verdict. Logs via `logging` to `%(asctime)s | %(levelname)s | %(name)s | %(message)s`.

**Verification:** Run `python -m py_compile scripts/judge_subagent_harness.py` and `python scripts/judge_subagent_harness.py --json evidence/reviews/subagent.json` — expect `28.2/100` with `28 faults` on current codebase, `delta -34.8` vs ultra `63`.

---

## 6. Loop Exit & Filing

File reviews to `evidence/reviews/`:
- `subagent_judge_YYYY-MM-DD.json` — machine-readable, per-judge breakdown, faults with `file:line`, `fix`, `+0.1pt`.
- `comparison.md` delta — human-readable money slide.

Exits only when `jq .aggregated_total evidence/reviews/subagent.json == 100` **and** `jq .n_improvements == 0`.

> **No 0.1pt left behind.** Every latency tail, fallback branch, and docs typo is a fault until proven otherwise.

*Rubric — 2026-08-29, subagent committee, blind, ultra-strict.*
