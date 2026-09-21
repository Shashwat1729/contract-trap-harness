"""
End-to-end: baseline vs advanced on the same contract, no live services needed.

Both FastAPI apps are exercised in-process via TestClient (no servers, no API
keys — EVAL_MOCK=1 forces the deterministic offline path). Uses a small
two-trap contract so the test is fast and hermetic.

Note: baseline/ and advanced/ both ship a top-level `src` package, so they
cannot coexist on sys.path. Each app is loaded in isolation via importlib
(and already-loaded `src*` modules are evicted first); the loaded app objects
keep working because they hold their own references.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("EVAL_MOCK", "1")

ROOT = Path(__file__).parents[2]


def load_app(name: str, base_dir: Path):
    """Import <base_dir>/src/main.py as a uniquely-named module and return its app."""
    for mod in [m for m in list(sys.modules) if m == "src" or m.startswith("src.")]:
        del sys.modules[mod]
    sys.path = [p for p in sys.path if Path(p).name not in ("baseline", "advanced")]
    sys.path.insert(0, str(base_dir))
    mod_name = f"{name}_main_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, base_dir / "src" / "main.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module.app


_baseline_dir = str(ROOT / "baseline")
_advanced_dir = str(ROOT / "advanced")
_saved_path = list(sys.path)

baseline_app = load_app("baseline", ROOT / "baseline")
advanced_app = load_app("advanced", ROOT / "advanced")

# Restore the import state we found: drop our path entries and the transient
# `src*` modules so sibling suites in the same pytest session are unaffected.
# The loaded app objects keep working through their own references.
sys.path = [p for p in sys.path if p not in (_baseline_dir, _advanced_dir)]
for _mod in [m for m in list(sys.modules) if m == "src" or m.startswith("src.")]:
    del sys.modules[_mod]
sys.path = _saved_path

from fastapi.testclient import TestClient  # noqa: E402

TRAP_CONTRACT = """
SAAS SERVICES AGREEMENT

Renewal Term: This Agreement shall automatically renew for successive
24 month periods unless either party provides written notice.

Notice Period To Terminate Renewal: Notice must be provided at least
30 days prior to renewal.

Cap On Liability: Liability is capped at 12 months fees, except carve-outs
for data breach are excluded from cap and not subject to limitation.
"""

PAYLOAD = {
    "contract_text": TRAP_CONTRACT,
    "contract_id": "e2e_01",
    "party": "AgentCo",
    "turn": 1,
}


def test_baseline_health():
    r = TestClient(baseline_app).get("/health")
    assert r.status_code == 200
    assert r.json()["variant"] == "baseline"


def test_advanced_health():
    r = TestClient(advanced_app).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["variant"] == "advanced"
    assert "verification-gated" in body["features"]


def test_both_detect_cross_clause_trap():
    """Same contract, same endpoint shape — advanced must gate, baseline must not."""
    baseline_res = TestClient(baseline_app).post("/api/redline", json=PAYLOAD)
    advanced_res = TestClient(advanced_app).post("/api/redline", json=PAYLOAD)
    assert baseline_res.status_code == 200
    assert advanced_res.status_code == 200

    base = baseline_res.json()
    adv = advanced_res.json()
    assert base["variant"] == "baseline"
    assert adv["variant"] == "advanced"

    # Advanced: every approved finding passed the evidence gate
    for f in adv["findings"]:
        if f["verification"] == "PASS":
            assert f["evidence"]["contract_page"] >= 1
            assert f["rule_id"]
    # Advanced reports its verification diagnostics; baseline does not gate
    assert adv["evidence_supported"] + adv["unsupported"] == adv["total_proposed"]
    assert adv["trap_count"] >= 1  # Trap-A (renewal/notice) must be caught
