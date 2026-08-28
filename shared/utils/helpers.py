"""Shared helpers — usable by baseline, advanced, and eval."""
import json, time
from pathlib import Path

def load_fixtures(path: str = "shared/fixtures/sample.json"):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {"queries": []}

def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - t0
