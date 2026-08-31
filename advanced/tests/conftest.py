import os

# Force the offline/mock LLM path for the default test session: deterministic, $0, no
# network dependency, matches the project's EVAL_MOCK=1 reproducibility convention.
# A real key may exist in advanced/.env on a dev machine -- tests must not silently
# spend it or become network-flaky. Opt-in live LLM tests explicitly unset this
# (see test_llm.py) and are skipped unless RUN_LIVE_LLM_TESTS=1 is set.
os.environ.setdefault("EVAL_MOCK", "1")
