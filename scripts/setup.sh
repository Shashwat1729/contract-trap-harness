#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Setup: Frontier Challenge — baseline + advanced"

if [ ! -d ".venv" ]; then
  echo "[setup] creating .venv (python 3.11)"
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

pip install --upgrade pip -q
echo "[setup] installing baseline deps"
pip install -r baseline/requirements.txt -q
echo "[setup] installing advanced deps"
pip install -r advanced/requirements.txt -q

if [ -f "package.json" ]; then
  echo "[setup] installing node deps"
  npm install --silent || true
fi

if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[setup] created .env from .env.example — fill keys if needed"
fi

echo "[setup] done — run 'make test' to verify"
