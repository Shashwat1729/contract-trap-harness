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

# `pip install --upgrade pip` (bare) can fail on Windows with "access is denied" --
# pip cannot always overwrite its own running executable in-place in that shell
# context. `python -m pip` avoids that (invokes pip as a module, not as the locked
# executable) and is also non-fatal here: upgrading pip itself is a nice-to-have,
# not required for the actual dependency installs below to succeed.
python -m pip install --upgrade pip -q || echo "[setup] pip self-upgrade skipped (non-fatal)"
echo "[setup] installing baseline deps"
python -m pip install -r baseline/requirements.txt -q
echo "[setup] installing advanced deps"
python -m pip install -r advanced/requirements.txt -q
echo "[setup] installing dashboard deps"
python -m pip install -r app/requirements.txt -q

if [ -f "package.json" ]; then
  echo "[setup] installing node deps"
  npm install --silent || true
fi

if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[setup] created .env from .env.example — fill keys if needed"
fi

echo "[setup] done — run 'make test' to verify"
