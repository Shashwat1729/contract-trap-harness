.PHONY: setup test test-unit test-integration test-e2e test-coverage run-baseline run-advanced run-all eval reproduce docker-build docker-setup docker-up docker-down kill pre-submit brief ingest-problem capture-trajectory help

ROOT := $(shell pwd)
PY := python
ifeq ($(OS),Windows_NT)
  VENV_PY := .venv/Scripts/python
  VENV_ACTIVATE := .venv/Scripts/activate
else
  VENV_PY := .venv/bin/python
  VENV_ACTIVATE := .venv/bin/activate
endif

help:
	@echo "Frontier Challenge — make targets"
	@echo "  make setup              — create venv + install deps"
	@echo "  make test               — unit+integration (no network)"
	@echo "  make test-e2e           — live e2e (needs make run-all)"
	@echo "  make run-baseline       — baseline on :8000"
	@echo "  make run-advanced       — advanced on :8001"
	@echo "  make run-all            — both via docker-compose"
	@echo "  make eval               — baseline vs advanced → evidence/benchmarks/"
	@echo "  make eval-mock          — eval without network (EVAL_MOCK=1)"
	@echo "  make reproduce          — full clean-env check (what judges run)"
	@echo "  make docker-build       — build images"
	@echo "  make kill               — free ports 8000/8001"
	@echo "  make pre-submit         — secret scan + reproduce + checks"
	@echo "  make ingest-problem PROBLEM_PDF=path.pdf — ingest kickoff PDF"
	@echo "  make brief              — distill PROBLEM.md → docs/problem-brief.md"

setup:
	bash scripts/setup.sh 2>/dev/null || (echo "[setup] bash not found — run manually: python -m venv .venv && pip install -r baseline/requirements.txt -r advanced/requirements.txt"; exit 1)

test: test-unit test-integration
	@echo "[test] all (non-e2e) passed"

test-unit:
	@echo "[test] baseline unit"
	cd baseline && $(PY) -m pytest tests/unit -v --tb=short
	@echo "[test] advanced unit"
	cd advanced && $(PY) -m pytest tests/unit -v --tb=short

test-integration:
	@echo "[test] baseline integration"
	cd baseline && $(PY) -m pytest tests/integration -v --tb=short
	@echo "[test] advanced integration"
	cd advanced && $(PY) -m pytest tests/integration -v --tb=short

test-e2e:
	$(PY) -m pytest tests/e2e -v --tb=short

test-coverage:
	cd baseline && $(PY) -m pytest --cov=src --cov-report=term --cov-report=html
	cd advanced && $(PY) -m pytest --cov=src --cov-report=term --cov-report=html

run-baseline:
	bash scripts/run_baseline.sh

run-advanced:
	bash scripts/run_advanced.sh

run-all:
	docker compose up --build -d
	@echo "baseline http://localhost:8000/health  advanced http://localhost:8001/health"

eval:
	bash scripts/eval.sh 2>/dev/null || python scripts/eval.py

eval-mock:
	EVAL_MOCK=1 bash scripts/eval.sh 2>/dev/null || python scripts/eval.py

reproduce:
	bash scripts/reproduce.sh 2>/dev/null || (echo "[reproduce] bash not found — running Windows fallback: tests + EVAL_MOCK=1 eval"; cd baseline && python -m pytest tests -v && cd ../advanced && python -m pytest tests -v && EVAL_MOCK=1 python scripts/eval.py)

docker-build:
	docker compose build

docker-setup: docker-build
	@echo "docker images built"

docker-up:
	docker compose up -d

docker-down:
	docker compose down

kill:
	-pkill -f "src.main" 2>/dev/null || true
	@echo "killed local servers (if any)"

pre-submit:
	@echo "[pre-submit] secret scan (basic)"; \
	if git grep -q "sk-" -- .env 2>/dev/null; then echo "WARN .env contains key-like string — not committed, ok"; fi; \
	if git diff --cached --name-only | xargs grep -l "sk-" 2>/dev/null; then echo "FAIL staged secrets"; exit 1; else echo "  no staged secrets"; fi
	@echo "[pre-submit] reproduce"; bash scripts/reproduce.sh
	@echo "[pre-submit] check comparison delta"; test -f evidence/benchmarks/comparison.md && echo "  comparison.md exists" || (echo "FAIL missing comparison.md"; exit 1)
	@echo "[pre-submit] check CHANGELOG"; grep -q "Improvement Changelog" CHANGELOG.md && echo "  CHANGELOG ok" || (echo "FAIL CHANGELOG"; exit 1)
	@echo "[pre-submit] ✅ pre-submit passed"

brief:
	@echo "[brief] PROBLEM.md → docs/problem-brief.md template already exists — fill manually or run ingest-problem"

ingest-problem:
	@echo "Usage: make ingest-problem PROBLEM_PDF=path.pdf or PROBLEM_URL=https://..."
	@test -n "$(PROBLEM_PDF)$(PROBLEM_URL)" || (echo "Set PROBLEM_PDF or PROBLEM_URL"; exit 1)
	@if [ -n "$(PROBLEM_PDF)" ]; then \
	  echo "ingesting $(PROBLEM_PDF)"; \
	  if command -v pdftotext >/dev/null 2>&1; then pdftotext "$(PROBLEM_PDF)" - | head -n 2000 > /tmp/ingest.txt && echo "preview at /tmp/ingest.txt"; fi; \
	  echo "→ paste into PROBLEM.md manually, then make brief"; \
	fi

capture-trajectory:
	bash scripts/capture_trajectory.sh "$(AGENT)" "$(TASK)"
