import os
import sys
from pathlib import Path

# Force the offline/mock LLM path for the default test session: deterministic, $0, no
# network dependency, matches the project's EVAL_MOCK=1 reproducibility convention.
# A real key may exist in advanced/.env on a dev machine -- tests must not silently
# spend it or become network-flaky. Opt-in live LLM tests explicitly unset this
# (see test_llm.py) and are skipped unless RUN_LIVE_LLM_TESTS=1 is set.
os.environ.setdefault("EVAL_MOCK", "1")

# Some test modules import via the absolute "advanced.src..." package path, others via
# "src..." (advanced/pyproject.toml's pythonpath=["."]). Put both the repo root and
# advanced/ on sys.path so the suite collects the same way whether pytest is invoked
# from the repo root (make reproduce) or from inside advanced/ (make test-unit).
_ADVANCED = Path(__file__).resolve().parents[1]
_ROOT = _ADVANCED.parent
for _p in (str(_ROOT), str(_ADVANCED)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
